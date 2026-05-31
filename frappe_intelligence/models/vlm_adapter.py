"""
vlm_adapter.py
--------------
Extracts field values by prompting a local Ollama Vision-Language Model.

Configuration (AI Settings Single DocType or site_config.json):
    ollama_base_url     default: "http://localhost:11434"
    ollama_model        default: "qwen2.5:7b"
    ollama_timeout      default: 60  (seconds per call)
    extraction_mode     default: "Batch with Fallback"
    keep_model_loaded   default: False

Extraction strategies (selectable in AI Settings → Chat tab → Extraction Behaviour)
-------------------------------------------------------------------------------------
Per Field           One Ollama call per VLM field. Slowest but most reliable.
Batch               One call for all fields at once. Fastest, less reliable on weak models.
Batch with Fallback Tries batch first; per-field retry for any field that returned None.
Parallel            Concurrent per-field calls. Fast without the batch JSON risk.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "qwen2.5:7b"
_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT = 60

_DEFAULT_EXTRACTION_MODE = "Batch with Fallback"
_PARALLEL_MAX_WORKERS = 4


# ---------------------------------------------------------------------------
# Module-level helpers (stateless, no class dependency)
# ---------------------------------------------------------------------------

def _eligible_rules(rules) -> list:
    """Return VLM-eligible rules that have an llm_hint defined."""
    return [
        r for r in rules
        if (r.extraction_strategy or "Regex").strip() != "Regex"
        and (r.llm_hint or "").strip()
    ]


def _confidence(matched: int, total: int) -> float:
    return matched / total if total else 0.0


def _parse_json(raw: str) -> tuple[dict | None, str | None]:
    """Strip markdown fences and parse JSON. Returns (data, error)."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    if not cleaned:
        return None, None
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError:
        return None, f"Model returned non-JSON: {cleaned[:200]}"


def _log_field_error(field_key: str, error: str) -> None:
    frappe.log_error(f"VLMAdapter error for field '{field_key}': {error}", "VLMAdapter")


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class VLMAdapter(LLMAdapter):
    """Ollama-backed VLM extractor with four configurable extraction strategies."""

    def __init__(self, model: str | None = None):
        self.model = (
            model
            or frappe.db.get_single_value("AI Settings", "ollama_model")
            or frappe.conf.get("ollama_model", _DEFAULT_MODEL)
        )
        base = (
            frappe.db.get_single_value("AI Settings", "ollama_base_url")
            or frappe.conf.get("ollama_base_url", _DEFAULT_BASE_URL)
        )
        self.base_url = base.rstrip("/")
        timeout = (
            frappe.db.get_single_value("AI Settings", "ollama_timeout")
            or frappe.conf.get("ollama_timeout", _DEFAULT_TIMEOUT)
        )
        self.timeout = int(timeout)
        self.keep_loaded = bool(
            frappe.db.get_single_value("AI Settings", "keep_model_loaded")
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, raw_text: str, rules) -> tuple[dict[str, Any], float]:
        """
        Extract field values using the strategy configured in AI Settings.

        Returns
        -------
        (result_dict, confidence_score)
        """
        mode = (
            frappe.db.get_single_value("AI Settings", "extraction_mode")
            or _DEFAULT_EXTRACTION_MODE
        )
        strategies = {
            "Per Field":           self._extract_per_field,
            "Batch":               self._extract_batch,
            "Batch with Fallback": self._extract_batch_with_fallback,
            "Parallel":            self._extract_parallel,
        }
        return strategies.get(mode, self._extract_batch_with_fallback)(raw_text, rules)

    def chat(
        self,
        prompt: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
    ) -> tuple[str | dict | None, str | None]:
        """
        Multi-turn conversational reply via Ollama /api/chat, with optional tools.

        Returns
        -------
        (reply_or_tool, error)
            reply_or_tool is either a plain string or
            {"__tool__": name, "args": {...}} when the model calls a tool.
        """
        try:
            import requests  # noqa: PLC0415
        except ImportError:
            return None, "requests library not available"

        system_text = (
            frappe.db.get_single_value("AI Settings", "system_prompt")
            or DEFAULT_CHAT_SYSTEM
        )
        messages = list(history or []) + [{"role": "user", "content": prompt}]

        payload: dict = {
            "model": self.model,
            "system": system_text,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in tools
            ]
        if self.keep_loaded:
            payload["keep_alive"] = -1

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                # Connect timeout: 10 s (fail fast when Ollama is not running).
                # Read timeout: configured value (default 60 s, streaming chunks).
                timeout=(min(self.timeout, 10), self.timeout),
                stream=True,
            )
        except requests.exceptions.ConnectionError:
            return None, f"Cannot connect to Ollama at {self.base_url}"
        except requests.exceptions.Timeout:
            return None, f"Ollama timed out after {self.timeout}s (model may be busy)"
        except requests.exceptions.RequestException as exc:
            return None, f"Ollama request failed: {exc}"

        if resp.status_code != 200:
            return None, f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"

        full_text = ""
        tool_call = None

        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                message = data.get("message", {})

                tc = message.get("tool_calls")
                if tc:
                    fn = tc[0].get("function", {})
                    name = fn.get("name")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    if name:
                        tool_call = {"__tool__": name, "args": args}

                chunk = message.get("content", "")
                if chunk:
                    full_text += chunk
                    publish_chunk(chunk)

                if data.get("done"):
                    break

            if tool_call:
                return tool_call, None
            return full_text.strip() or None, None

        except Exception as exc:  # noqa: BLE001
            return None, f"Ollama streaming error: {exc}"
        finally:
            # Always signal end-of-stream so the browser clears the
            # streaming flag, even when an exception short-circuits the loop.
            publish_done()

    # ------------------------------------------------------------------
    # Extraction strategies
    # (Each filters rules internally, then delegates to the matching runner.)
    # ------------------------------------------------------------------

    def _extract_per_field(self, raw_text: str, rules) -> tuple[dict, float]:
        """One Ollama call per field. Slowest but most reliable."""
        return self._run_per_field(raw_text, _eligible_rules(rules))

    def _extract_batch(self, raw_text: str, rules) -> tuple[dict, float]:
        """One Ollama call for all fields. Fastest, less reliable on weak models."""
        return self._run_batch(raw_text, _eligible_rules(rules))

    def _extract_batch_with_fallback(self, raw_text: str, rules) -> tuple[dict, float]:
        """Batch first; per-field retry for any field that returned None."""
        eligible = _eligible_rules(rules)
        if not eligible:
            return {}, 0.0

        result, _ = self._run_batch(raw_text, eligible)

        retry = [r for r in eligible if result.get(r.field_key) is None]
        if retry:
            fallback, _ = self._run_per_field(raw_text, retry)
            result.update(fallback)

        matched = sum(1 for v in result.values() if v)
        return result, _confidence(matched, len(eligible))

    def _extract_parallel(self, raw_text: str, rules) -> tuple[dict, float]:
        """Concurrent per-field calls. Fast without batch JSON reliability risk."""
        return self._run_parallel(raw_text, _eligible_rules(rules))

    # ------------------------------------------------------------------
    # Strategy runners
    # (Operate on a pre-filtered eligible list — no further rule filtering.)
    # ------------------------------------------------------------------

    def _run_per_field(self, raw_text: str, eligible: list) -> tuple[dict, float]:
        result: dict[str, Any] = {}
        matched = 0
        for rule in eligible:
            value, error = self._query_field(raw_text, rule.llm_hint.strip())
            if error:
                _log_field_error(rule.field_key, error)
                result[rule.field_key] = None
            else:
                result[rule.field_key] = value
                if value:
                    matched += 1
        return result, _confidence(matched, len(eligible))

    def _run_batch(self, raw_text: str, eligible: list) -> tuple[dict, float]:
        if not eligible:
            return {}, 0.0
        raw, error = self._generate(self._build_batch_prompt(raw_text, eligible))
        if error:
            frappe.log_error(f"VLMAdapter batch extraction failed: {error}", "VLMAdapter")
            return {r.field_key: None for r in eligible}, 0.0
        result = self._parse_batch_reply(raw, eligible)
        matched = sum(1 for v in result.values() if v)
        return result, _confidence(matched, len(eligible))

    def _run_parallel(self, raw_text: str, eligible: list) -> tuple[dict, float]:
        if not eligible:
            return {}, 0.0

        result: dict[str, Any] = {}
        matched = 0

        def _fetch(rule):
            value, error = self._query_field(raw_text, rule.llm_hint.strip())
            return rule.field_key, value, error

        workers = min(len(eligible), _PARALLEL_MAX_WORKERS)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_fetch, r) for r in eligible]
            for future in as_completed(futures):
                field_key, value, error = future.result()
                if error:
                    _log_field_error(field_key, error)
                    result[field_key] = None
                else:
                    result[field_key] = value
                    if value:
                        matched += 1

        return result, _confidence(matched, len(eligible))

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_field_prompt(raw_text: str, hint: str) -> str:
        """Single-field prompt: model must return {"value": "..."}."""
        return (
            f"{hint}\n\n"
            'Return ONLY a JSON object with a single key "value" containing '
            'the extracted text. If the information is not present, return {"value": null}.\n\n'
            f"Document text:\n---\n{raw_text[:4000]}\n---"
        )

    @staticmethod
    def _build_batch_prompt(raw_text: str, eligible: list) -> str:
        """Multi-field prompt: model must return {field_key: value, ...}."""
        fields_block = "\n".join(
            f'  "{r.field_key}": {(r.llm_hint or "").strip()}'
            for r in eligible
        )
        null_example = ", ".join(f'"{r.field_key}": null' for r in eligible)
        return (
            "Extract the following fields from the document below.\n"
            "Return ONLY a single valid JSON object using these exact keys.\n"
            "Use null for any field not found in the document.\n\n"
            f"Fields to extract:\n{fields_block}\n\n"
            f"Response format: {{{null_example}}}\n\n"
            f"Document text:\n---\n{raw_text[:4000]}\n---"
        )

    # ------------------------------------------------------------------
    # Low-level Ollama call
    # ------------------------------------------------------------------

    def _query_field(self, raw_text: str, hint: str) -> tuple[str | None, str | None]:
        """Build a single-field prompt, generate, and parse {"value": ...}."""
        raw, error = self._generate(self._build_field_prompt(raw_text, hint))
        if error:
            return None, error
        return self._parse_single_reply(raw)

    def _generate(self, prompt: str) -> tuple[str | None, str | None]:
        """POST to Ollama /api/generate. Returns (response_text, error)."""
        try:
            import requests  # noqa: PLC0415
        except ImportError:
            return None, "requests library not available"

        payload: dict = {
            "model": self.model,
            "system": EXTRACTION_SYSTEM,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        if self.keep_loaded:
            payload["keep_alive"] = -1

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError:
            return None, f"Cannot connect to Ollama at {self.base_url}"
        except requests.exceptions.Timeout:
            return None, f"Ollama timed out after {self.timeout}s (model may be busy)"
        except requests.exceptions.RequestException as exc:
            return None, f"Ollama request failed: {exc}"

        if resp.status_code != 200:
            return None, f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"

        return resp.json().get("response", "").strip(), None

    # ------------------------------------------------------------------
    # Reply parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_single_reply(raw: str) -> tuple[str | None, str | None]:
        """Parse {"value": ...} from a raw /api/generate response."""
        data, error = _parse_json(raw)
        if error:
            return None, error
        if data is None:
            return None, None
        value = data.get("value")
        return (str(value).strip() or None) if value is not None else None, None

    @staticmethod
    def _parse_batch_reply(raw: str, eligible: list) -> dict:
        """Parse a multi-field JSON dict from a batch /api/generate response."""
        data, error = _parse_json(raw)
        if error or data is None:
            if error:
                frappe.log_error(f"VLMAdapter batch parse error: {error}", "VLMAdapter")
            return {r.field_key: None for r in eligible}
        return {
            r.field_key: (str(data[r.field_key]).strip() or None)
            if data.get(r.field_key) is not None else None
            for r in eligible
        }

