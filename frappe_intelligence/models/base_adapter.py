"""Base class and shared utilities for all LLM adapters.

Every concrete adapter (Claude, Ollama, Gemini, …) must:
  1. Inherit from LLMAdapter.
  2. Implement extract() and chat().

Shared items kept here to avoid duplication across adapters:
  - _EXTRACTION_SYSTEM, _DEFAULT_CHAT_SYSTEM  (prompt constants)
  - _publish_chunk(), _publish_done()          (realtime streaming)
  - parse_json_reply()                         ({"value": ...} parser)
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


# ---------------------------------------------------------------------------
# Shared prompt constants
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM = (
    "You are a precise document data-extraction assistant. "
    "You MUST respond with a single valid JSON object and absolutely nothing else — "
    "no explanation, no markdown, no code fences. "
    'Example response format: {"value": "<extracted text>"}'
)

DEFAULT_CHAT_SYSTEM = (
    "You are a helpful assistant integrated with a Frappe-based business application. "
    "Answer concisely and accurately. Reply in the same language the user uses."
)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMAdapter(ABC):
    """Common interface every LLM adapter must implement."""

    @abstractmethod
    def extract(self, raw_text: str, rules: list) -> tuple[dict[str, Any], float]:
        """Extract labelled fields from *raw_text* using *rules*.

        Returns
        -------
        (result_dict, confidence)
            result_dict  — {field_key: value_or_None}
            confidence   — fraction of VLM-eligible fields that returned a value (0.0–1.0)
        """

    @abstractmethod
    def chat(
        self,
        prompt: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
    ) -> tuple[str | dict | None, str | None]:
        """Send *prompt* to the model and return a reply.

        Parameters
        ----------
        prompt:  Current user message (may include context and language rule).
        history: Previous turns as [{"role": "user"|"assistant", "content": str}].
        tools:   Neutral tool definitions:
                 [{"name": str, "description": str, "parameters": {...}}, ...]

        Returns
        -------
        (reply_or_tool, error)
            reply_or_tool — plain string, or {"__tool__": name, "args": {...}}
            Exactly one of the two will be non-None.
        """


# ---------------------------------------------------------------------------
# Shared helpers — used by any adapter, importable at module level
# ---------------------------------------------------------------------------

def parse_json_reply(raw: str) -> tuple[str | None, str | None]:
    """Parse a {"value": ...} reply from any extraction-mode model call.

    Returns (value, error). Both may be None (field genuinely absent).
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    if not cleaned:
        return None, None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r'"value"\s*:\s*"([^"]*)"', cleaned)
        if m:
            return m.group(1).strip() or None, None
        return None, f"Model returned non-JSON: {cleaned[:200]}"

    value = data.get("value")
    if value is None:
        return None, None
    return str(value).strip() or None, None


def publish_chunk(text: str) -> None:
    """Stream one token to the browser via Frappe realtime (silent no-op outside request context)."""
    try:
        import frappe as _f  # noqa: PLC0415
        _f.publish_realtime("ai_stream_chunk", {"chunk": text, "done": False}, user=_f.session.user)
    except Exception:  # noqa: BLE001
        pass


def publish_done() -> None:
    """Signal end-of-stream to the browser."""
    try:
        import frappe as _f  # noqa: PLC0415
        _f.publish_realtime("ai_stream_chunk", {"chunk": "", "done": True}, user=_f.session.user)
    except Exception:  # noqa: BLE001
        pass
