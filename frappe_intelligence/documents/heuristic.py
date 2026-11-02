"""
heuristic.py
------------
High-speed field extractor using compiled regular expressions.

The extractor iterates over AI Extraction Rule rows, applies the
``regex_pattern`` against the raw OCR/PDF text, and computes a
confidence score based on how many *required* fields were matched.
"""

from __future__ import annotations

import re
from typing import Any

# Flags applied to every pattern
_RE_FLAGS = re.IGNORECASE | re.MULTILINE | re.UNICODE


class HeuristicExtractor:
	"""Regex-based field extractor."""

	def extract(self, raw_text: str, rules) -> tuple[dict[str, Any], float]:
		"""
		Run each rule's ``regex_pattern`` against *raw_text*.

		Rules with ``extraction_strategy == "VLM"`` are skipped (handled
		by the VLMAdapter).

		Returns
		-------
		tuple of:
		    result_dict  — ``{field_key: matched_value_or_None, ...}``
		    confidence   — fraction of non-VLM rules that produced a match
		                   (0.0 - 1.0).  Only rules that have a pattern
		                   defined count toward the denominator.
		"""
		result: dict[str, Any] = {}
		total_countable = 0
		matched = 0

		for rule in rules:
			strategy = (rule.extraction_strategy or "Regex").strip()
			if strategy == "VLM":
				# Delegate entirely to VLMAdapter: don't populate key here
				continue

			field_key = rule.field_key
			pattern = (rule.regex_pattern or "").strip()

			if not pattern:
				# No pattern defined; record None but don't penalise score
				result[field_key] = None
				continue

			total_countable += 1

			try:
				match = re.search(pattern, raw_text, _RE_FLAGS)
			except re.error as exc:
				frappe_log(
					f"Invalid regex for field '{field_key}': {exc}",
					"HeuristicExtractor",
				)
				result[field_key] = None
				continue

			if match:
				# Prefer the first capturing group if one exists, otherwise
				# return the full match (group 0).
				value = match.group(1) if match.lastindex else match.group(0)
				result[field_key] = value.strip()
				matched += 1
			else:
				result[field_key] = None

		confidence = matched / total_countable if total_countable else 0.0
		return result, confidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def frappe_log(message: str, title: str) -> None:
	"""Log to Frappe error log without crashing if frappe is unavailable."""
	try:
		import frappe as _frappe

		_frappe.log_error(message, title)
	except Exception:
		pass
