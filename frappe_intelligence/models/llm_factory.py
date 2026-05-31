"""
llm_factory.py
--------------
Returns the configured LLM adapter based on the AI Settings Single DocType.

All adapters inherit from LLMAdapter (models/base_adapter.py) and expose:
    extract(raw_text, rules) -> (dict, float)   — document field extraction
    chat(prompt, history, tools) -> (reply, error) — conversational queries

Adding a new provider:
  1. Create models/<name>_adapter.py inheriting LLMAdapter, implement extract() + chat().
  2. Add a new option in AI Settings "ai_provider" Select field.
  3. Add a branch in _build_primary() below.

Supported providers: Ollama, Claude, Gemini.
"""
from __future__ import annotations

import frappe


def get_adapter():
    """
    Return an LLM adapter instance configured by AI Settings.

    Cached in frappe.local for the duration of the current request so that
    multiple calls within the same HTTP request (e.g. tool resolution) don't
    repeat the 6-8 DB reads required to build the adapter.

    When "Enable Ollama Fallback" is ticked and the primary provider is not
    Ollama, the returned adapter silently retries with Ollama if the primary
    call fails (connection error, auth error, rate limit, etc.).

    Falls back to plain Ollama if the settings cannot be read (e.g. during
    install before the DocType exists).
    """
    # frappe.local is request-scoped — reuse within a single HTTP request.
    cached = getattr(frappe.local, "_fi_adapter", None)
    if cached is not None:
        return cached

    try:
        provider = frappe.db.get_single_value("AI Settings", "ai_provider") or "Ollama"
        fallback_enabled = bool(
            frappe.db.get_single_value("AI Settings", "enable_ollama_fallback")
        )
    except Exception:
        provider = "Ollama"
        fallback_enabled = False

    primary = _build_primary(provider)

    if fallback_enabled and provider != "Ollama":
        from frappe_intelligence.models.vlm_adapter import VLMAdapter
        adapter = _FallbackAdapter(primary, VLMAdapter())
    else:
        adapter = primary

    frappe.local._fi_adapter = adapter
    return adapter


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_primary(provider: str):
    if provider == "Claude":
        from frappe_intelligence.models.claude_adapter import ClaudeAdapter
        return ClaudeAdapter()

    if provider == "Gemini":
        from frappe_intelligence.models.gemini_adapter import GeminiAdapter
        return GeminiAdapter()

    # Default: Ollama
    from frappe_intelligence.models.vlm_adapter import VLMAdapter
    return VLMAdapter()


class _FallbackAdapter:
    """
    Wraps a primary adapter and retries with Ollama on failure.

    Fallback triggers:
      chat()    — when the primary returns a non-None error string.
      extract() — when every VLM-eligible field in the result is None
                  (indicates a connection / auth failure, not just "not found").
    """

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback

    def chat(
        self,
        prompt: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
    ) -> tuple[str | dict | None, str | None]:
        reply, error = self._primary.chat(prompt, history=history, tools=tools)
        if error:
            _log_fallback("chat", error)
            return self._fallback.chat(prompt, history=history, tools=tools)
        return reply, error

    def extract(self, raw_text: str, rules) -> tuple[dict, float]:
        result, confidence = self._primary.extract(raw_text, rules)

        # Only fall back when every VLM-eligible field is None — that pattern
        # indicates the primary adapter could not reach the model at all.
        vlm_rules = [
            r for r in rules
            if (r.extraction_strategy or "Regex").strip() != "Regex"
        ]
        all_none = vlm_rules and all(result.get(r.field_key) is None for r in vlm_rules)

        if all_none:
            _log_fallback("extract", "all VLM fields returned None")
            return self._fallback.extract(raw_text, rules)

        return result, confidence


def _log_fallback(method: str, reason: str) -> None:
    try:
        frappe.log_error(
            title=f"LLMFactory: primary adapter failed on {method}() — switching to Ollama fallback",
            message=reason,
        )
    except Exception:
        pass
