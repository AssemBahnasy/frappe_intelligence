"""
gemini_adapter.py
-----------------
LLM adapter backed by the Google Gemini API (google-genai SDK).

Configuration (AI Settings Single DocType):
    gemini_api_key   — Google API key from aistudio.google.com (required)
    gemini_model     — Model ID (default: gemini-2.0-flash)
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

_DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiAdapter(LLMAdapter):
    """Google Gemini-backed extractor and chat assistant."""

    def __init__(self):
        try:
            from frappe.utils.password import get_decrypted_password
            self.api_key = (
                get_decrypted_password("AI Settings", "AI Settings", "gemini_api_key", raise_exception=False)
                or frappe.conf.get("gemini_api_key", "")
            )
        except Exception:
            self.api_key = frappe.conf.get("gemini_api_key", "")

        self.model = (
            frappe.db.get_single_value("AI Settings", "gemini_model")
            or frappe.conf.get("gemini_model", _DEFAULT_MODEL)
        )
        self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, raw_text: str, rules: list) -> tuple[dict[str, Any], float]:
        """Per-field extraction using Gemini with JSON output mode."""
        client, err = self._get_client()
        if err:
            return {r.field_key: None for r in rules}, 0.0

        result: dict[str, Any] = {}
        total = matched = 0

        for rule in rules:
            strategy = (rule.extraction_strategy or "Regex").strip()
            if strategy == "Regex":
                continue

            hint = (rule.llm_hint or "").strip()
            if not hint:
                result[rule.field_key] = None
                continue

            total += 1
            value, error = self._extract_field(client, raw_text, hint)

            if error:
                frappe.log_error(
                    f"GeminiAdapter error for field '{rule.field_key}': {error}",
                    "GeminiAdapter",
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
        """Multi-turn chat with optional Frappe tool use and token streaming."""
        client, err = self._get_client()
        if err:
            return None, err

        try:
            from google.genai import types
        except ImportError:
            return None, (
                "The 'google-genai' package is not installed. "
                "Run: bench pip install google-genai"
            )

        system_text = (
            frappe.db.get_single_value("AI Settings", "system_prompt")
            or DEFAULT_CHAT_SYSTEM
        )

        contents = _to_gemini_history(history, types)
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        )

        config_kwargs: dict[str, Any] = {
            "system_instruction": system_text,
        }
        if tools:
            config_kwargs["tools"] = _to_gemini_tools(tools, types)

        config = types.GenerateContentConfig(**config_kwargs)

        try:
            full_text = ""
            tool_call = None

            for chunk in client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            ):
                if not chunk.candidates:
                    continue
                candidate = chunk.candidates[0]
                # Some chunks (e.g. the final usage-stats chunk) have candidates
                # but content=None — skip them to avoid AttributeError.
                if not candidate.content or not candidate.content.parts:
                    continue
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_call = part.function_call
                    elif hasattr(part, "text") and part.text:
                        full_text += part.text
                        publish_chunk(part.text)

            if tool_call:
                return {"__tool__": tool_call.name, "args": dict(tool_call.args)}, None

            return full_text.strip() or None, None

        except Exception as exc:  # noqa: BLE001
            return None, self._friendly_error(exc)
        finally:
            # Always signal end-of-stream so the browser clears _isStreaming,
            # even when an exception short-circuits the loop above.
            publish_done()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_field(
        self, client, raw_text: str, hint: str
    ) -> tuple[str | None, str | None]:
        try:
            from google.genai import types
        except ImportError:
            return None, "google-genai not installed"

        prompt = (
            f"{hint}\n\n"
            "Return ONLY a JSON object with a single key 'value' containing "
            "the extracted text. If not present, return {\"value\": null}.\n\n"
            "Document text:\n---\n"
            f"{raw_text[:4000]}\n---"
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM,
                    response_mime_type="application/json",
                ),
            )
            raw_reply = response.text.strip() if response.text else ""
            return parse_json_reply(raw_reply)
        except Exception as exc:  # noqa: BLE001
            return None, self._friendly_error(exc)

    def test_connection(self) -> tuple[bool, str | None]:
        """Lightweight connectivity check — validates API key without a full generation call."""
        client, err = self._get_client()
        if err:
            return False, err
        try:
            client.models.get(model=self.model)
            return True, None
        except Exception as exc:
            return False, self._friendly_error(exc)

    def _get_client(self):
        """Return (google.genai.Client, None) or (None, error_message)."""
        if self._client is not None:
            return self._client, None

        if not self.api_key:
            return None, (
                "Gemini API key is not configured. "
                "Open AI Settings and enter your Google API key."
            )

        try:
            from google import genai
        except ImportError:
            return None, (
                "The 'google-genai' package is not installed. "
                "Run: bench pip install google-genai"
            )

        # google-genai HttpOptions.timeout is in milliseconds.
        # Config value is in seconds for readability; convert here.
        timeout_s = float(frappe.conf.get("gemini_timeout", 60))
        timeout_ms = int(timeout_s * 1000)
        try:
            self._client = genai.Client(
                api_key=self.api_key,
                http_options={"timeout": timeout_ms},
            )
        except TypeError:
            # Older SDK versions that don't accept http_options — no timeout.
            self._client = genai.Client(api_key=self.api_key)
        return self._client, None

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        name = type(exc).__name__
        msg = str(exc)
        if "API_KEY_INVALID" in msg or "INVALID_ARGUMENT" in msg or "API key not valid" in msg or "401" in msg or "403" in msg:
            return "Invalid Gemini API key. Please check AI Settings."
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            return "Gemini API quota exceeded. Please wait and try again."
        if "ConnectionError" in name or "connect" in msg.lower():
            return "Cannot connect to the Gemini API. Check your internet connection."
        if "timed out" in msg.lower() or "TimeoutError" in name or "Timeout" in name:
            return (
                "Gemini API request timed out. This may be a temporary network issue. "
                "You can increase the timeout in site_config.json: {\"gemini_timeout\": 120}"
            )
        return f"Gemini API error: {msg}"


# ---------------------------------------------------------------------------
# Format converters
# ---------------------------------------------------------------------------

def _to_gemini_history(history: list[dict] | None, types) -> list:
    """Convert neutral [{role, content}] history to Gemini Content objects."""
    contents = []
    for turn in (history or []):
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])])
        )
    return contents


def _to_gemini_tools(tools: list[dict], types) -> list:
    """Convert neutral tool definitions to a Gemini Tool list."""
    _TYPE_MAP = {
        "string": "STRING",
        "number": "NUMBER",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "object": "OBJECT",
        "array": "ARRAY",
    }

    declarations = []
    for t in tools:
        params = t.get("parameters", {})
        props = {}
        for k, v in params.get("properties", {}).items():
            gemini_type = getattr(types.Type, _TYPE_MAP.get(v.get("type", "string").lower(), "STRING"))
            props[k] = types.Schema(
                type=gemini_type,
                description=v.get("description", ""),
            )

        declarations.append(
            types.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=props,
                    required=params.get("required", []),
                ),
            )
        )

    return [types.Tool(function_declarations=declarations)]
