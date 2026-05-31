"""
claude_adapter.py
-----------------
LLM adapter backed by the Anthropic Claude API.

Configuration (AI Settings Single DocType):
    claude_api_key   — Anthropic API key (required)
    claude_model     — Model ID (default: claude-haiku-4-5-20251001)

System prompt sent with cache_control=ephemeral for prompt caching.
"""
from __future__ import annotations

from typing import Any

import frappe
from frappe_intelligence.models.base_adapter import (
    DEFAULT_CHAT_SYSTEM,
    EXTRACTION_SYSTEM,
    LLMAdapter,
    parse_json_reply,
    publish_chunk,
    publish_done,
)

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude-backed extractor and chat assistant."""

    def __init__(self):
        try:
            from frappe.utils.password import get_decrypted_password  # noqa: PLC0415
            self.api_key = (
                get_decrypted_password("AI Settings", "AI Settings", "claude_api_key", raise_exception=False)
                or frappe.conf.get("claude_api_key", "")
            )
        except Exception:
            self.api_key = frappe.conf.get("claude_api_key", "")
        self.model = (
            frappe.db.get_single_value("AI Settings", "claude_model") or
            frappe.conf.get("claude_model", _DEFAULT_MODEL)
        )
        self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, raw_text: str, rules) -> tuple[dict[str, Any], float]:
        """
        Call Claude for each rule whose strategy is VLM or Both.

        Rules with strategy == "Regex" are skipped (handled by HeuristicAdapter).

        Returns
        -------
        (result_dict, confidence)  where confidence = fraction of VLM-eligible
        rules that returned a non-None value.
        """
        result: dict[str, Any] = {}
        total = 0
        matched = 0

        for rule in rules:
            strategy = (rule.extraction_strategy or "Regex").strip()
            if strategy == "Regex":
                continue

            hint = (rule.llm_hint or "").strip()
            if not hint:
                result[rule.field_key] = None
                continue

            total += 1
            value, error = self._extract_field(raw_text, hint)

            if error:
                frappe.log_error(
                    f"ClaudeAdapter error for field '{rule.field_key}': {error}",
                    "ClaudeAdapter",
                )
                result[rule.field_key] = None
            else:
                result[rule.field_key] = value
                if value:
                    matched += 1

        confidence = matched / total if total else 0.0
        return result, confidence

    def chat(
        self,
        prompt: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
    ) -> tuple[str | dict | None, str | None]:
        """
        Multi-turn assistant reply, with optional Frappe action tools.

        Parameters
        ----------
        prompt:
            The current user message (may include context hints and lang rule).
        history:
            Previous turns as ``[{"role": "user"|"assistant", "content": str}, ...]``.
            Pass ``None`` or ``[]`` for a fresh single-turn call.
        tools:
            Optional list of tool definitions in neutral format
            ``[{"name": str, "description": str, "parameters": {...}}, ...]``.
            When provided, Claude may return a tool call instead of plain text.

        Returns
        -------
        (reply_or_tool, error)
            reply_or_tool is either a plain string or a dict
            ``{"__tool__": name, "args": {...}}`` when the model calls a tool.
            Exactly one of (reply_or_tool, error) will be non-None.
        """
        client, err = self._get_client()
        if err:
            return None, err

        system_text = (
            frappe.db.get_single_value("AI Settings", "system_prompt") or
            DEFAULT_CHAT_SYSTEM
        )
        messages = list(history or []) + [{"role": "user", "content": prompt}]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "system": [
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": messages,
        }

        if tools:
            # Convert neutral format → Claude format
            kwargs["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]

        try:
            with client.messages.stream(**kwargs) as stream:
                full_text = ""
                for text_chunk in stream.text_stream:
                    full_text += text_chunk
                    publish_chunk(text_chunk)

                # Inspect the final assembled message for tool use
                final_msg = stream.get_final_message()
                for block in final_msg.content:
                    if getattr(block, "type", None) == "tool_use":
                        publish_done()
                        return {"__tool__": block.name, "args": block.input}, None

            publish_done()
            return full_text.strip() or None, None
        except Exception as exc:  # noqa: BLE001
            return None, self._friendly_error(exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_field(self, raw_text: str, hint: str) -> tuple[str | None, str | None]:
        client, err = self._get_client()
        if err:
            return None, err

        prompt = (
            f"{hint}\n\n"
            "Return ONLY a JSON object with a single key 'value' containing "
            "the extracted text. If the information is not present, return "
            '{"value": null}.\n\n'
            "Document text:\n"
            "---\n"
            f"{raw_text[:4000]}\n"
            "---"
        )

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=256,
                system=[
                    {
                        "type": "text",
                        "text": EXTRACTION_SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": prompt}],
            )
            raw_reply = response.content[0].text.strip()
            return parse_json_reply(raw_reply)
        except Exception as exc:  # noqa: BLE001
            return None, self._friendly_error(exc)

    def _get_client(self):
        """
        Return (anthropic.Anthropic client, None) or (None, error_message).
        """
        if self._client is not None:
            return self._client, None

        if not self.api_key:
            return None, (
                "Claude API key is not configured. "
                "Open AI Settings and enter your Anthropic API key."
            )

        try:
            import anthropic  # noqa: PLC0415
        except ImportError:
            return None, (
                "The 'anthropic' Python package is not installed. "
                "Run: bench pip install anthropic"
            )

        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client, None

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        name = type(exc).__name__
        msg = str(exc)
        if "AuthenticationError" in name or "401" in msg:
            return "Invalid Claude API key. Please check AI Settings."
        if "ConnectionError" in name or "connect" in msg.lower():
            return "Cannot connect to the Claude API. Check your internet connection."
        if "RateLimitError" in name or "429" in msg:
            return "Claude API rate limit reached. Please wait a moment and try again."
        return f"Claude API error: {msg}"
