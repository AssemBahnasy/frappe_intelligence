"""Pull field values out of document text with the AI provider chosen in AI Settings.

Strategies (AI Settings → Extraction Mode):
	Per Field            one call per field; slowest, most reliable
	Batch                one call for all fields; fastest, weaker on small models
	Batch with Fallback  batch first, then per-field for anything it missed
	Parallel             per-field calls run concurrently
"""

from __future__ import annotations

import contextvars
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import frappe

from frappe_intelligence.providers import Message, ProviderError, get_provider

SYSTEM = (
	"You are a precise document data-extraction assistant. "
	"Respond with a single valid JSON object and nothing else: no explanation, no markdown, no code fences."
)
MAX_DOCUMENT_CHARS = 4000
PARALLEL_WORKERS = 4
DEFAULT_MODE = "Batch with Fallback"
STRATEGIES = {
	"Per Field": "per_field",
	"Batch": "batch",
	"Batch with Fallback": "batch_with_fallback",
	"Parallel": "parallel",
}


def extract(raw_text: str, rules, strict: bool = False) -> tuple[dict[str, Any], float]:
	"""Return `({field_key: value or None}, share of AI fields that got a value)`.

	`strict`: raise the ProviderError when the AI could not be reached and nothing was found, instead
	of returning empty values that look like "not in the text".
	"""
	eligible = [
		rule
		for rule in rules
		if (rule.extraction_strategy or "Regex").strip() != "Regex" and (rule.llm_hint or "").strip()
	]
	if not eligible:
		return {}, 0.0

	extractor = _Extractor(raw_text[:MAX_DOCUMENT_CHARS])
	mode = frappe.get_cached_doc("AI Settings").extraction_mode or DEFAULT_MODE
	result = getattr(extractor, STRATEGIES.get(mode, STRATEGIES[DEFAULT_MODE]))(eligible)
	if extractor.errors:
		frappe.log_error("AI field extraction", "\n".join(extractor.errors))
	if strict and extractor.unreachable and not any(result.values()):
		raise extractor.unreachable
	return result, sum(1 for value in result.values() if value) / len(eligible)


class _Extractor:
	def __init__(self, text: str):
		self.text = text
		self.provider = get_provider()
		self.errors: list[str] = []
		self.unreachable: ProviderError | None = None

	def per_field(self, rules) -> dict:
		return {rule.field_key: self.field(rule) for rule in rules}

	def parallel(self, rules) -> dict:
		# Each task gets its own copy of the request context so frappe.local works in the thread.
		with ThreadPoolExecutor(max_workers=min(len(rules), PARALLEL_WORKERS)) as pool:
			futures = {
				rule.field_key: pool.submit(contextvars.copy_context().run, self.field, rule)
				for rule in rules
			}
		return {field_key: future.result() for field_key, future in futures.items()}

	def batch(self, rules) -> dict:
		fields = "\n".join(f'  "{rule.field_key}": {rule.llm_hint.strip()}' for rule in rules)
		shape = ", ".join(f'"{rule.field_key}": null' for rule in rules)
		data = self._ask(
			"Extract the following fields from the document below.\n"
			"Return ONLY a single valid JSON object using these exact keys.\n"
			"Use null for any field not found in the document.\n\n"
			f"Fields to extract:\n{fields}\n\n"
			f"Response format: {{{shape}}}\n\n"
			f"Document text:\n---\n{self.text}\n---"
		)
		return {rule.field_key: _clean(data.get(rule.field_key)) for rule in rules}

	def batch_with_fallback(self, rules) -> dict:
		result = self.batch(rules)
		missing = [rule for rule in rules if result[rule.field_key] is None]
		return result | self.per_field(missing) if missing else result

	def field(self, rule) -> str | None:
		data = self._ask(
			f"{rule.llm_hint.strip()}\n\n"
			'Return ONLY a JSON object with a single key "value" containing the extracted text. '
			'If the information is not present, return {"value": null}.\n\n'
			f"Document text:\n---\n{self.text}\n---"
		)
		return _clean(data.get("value"))

	def _ask(self, prompt: str) -> dict:
		try:
			reply = self.provider.complete(
				[Message(role="user", content=prompt)], system=SYSTEM, json_mode=True
			)
		except ProviderError as exc:
			self.errors.append(str(exc))
			self.unreachable = exc
			return {}
		data = _parse_json(reply.text)
		if data is None:
			self.errors.append(f"Model returned non-JSON: {reply.text[:200]}")
		return data or {}


def _parse_json(raw: str) -> dict | None:
	cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
	if not cleaned:
		return {}
	try:
		data = json.loads(cleaned)
	except json.JSONDecodeError:
		return None
	return data if isinstance(data, dict) else None


def _clean(value) -> str | None:
	return (str(value).strip() or None) if value is not None else None
