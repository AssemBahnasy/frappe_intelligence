"""Document field extraction over a fake provider."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch

from frappe_intelligence.documents import extractor
from frappe_intelligence.providers import ProviderError, Reply

RULES = [
	NS(field_key="invoice_no", llm_hint="The invoice number", extraction_strategy="LLM"),
	NS(field_key="total", llm_hint="The grand total", extraction_strategy="LLM"),
	NS(field_key="vat_no", llm_hint="", extraction_strategy="LLM"),
	NS(field_key="date", llm_hint="The date", extraction_strategy="Regex"),
]


class FakeProvider:
	"""Answers a batch prompt with only the invoice number, and per-field prompts by hint."""

	def __init__(self, fail=False):
		self.fail = fail
		self.prompts = []

	def complete(self, messages, **kwargs):
		prompt = messages[0].content
		self.prompts.append(prompt)
		if self.fail:
			raise ProviderError("offline")
		if prompt.startswith("Extract the following fields"):
			return Reply(text=json.dumps({"invoice_no": "INV-7", "total": None}))
		return Reply(text=json.dumps({"value": "1,500.00" if "grand total" in prompt else "INV-7"}))


class TestExtractor(TestCase):
	def run_extract(self, mode, provider):
		with (
			patch.object(extractor, "get_provider", return_value=provider),
			patch.object(extractor.frappe, "get_cached_doc", return_value=NS(extraction_mode=mode)),
			patch.object(extractor.frappe, "log_error") as log_error,
		):
			result = extractor.extract("Invoice INV-7 total 1,500.00", RULES)
		return result, log_error

	def test_batch_with_fallback_asks_again_only_for_missing_fields(self):
		provider = FakeProvider()
		(result, confidence), _ = self.run_extract("Batch with Fallback", provider)
		self.assertEqual(result, {"invoice_no": "INV-7", "total": "1,500.00"})
		self.assertEqual(confidence, 1.0)
		self.assertEqual(len(provider.prompts), 2)
		self.assertIn("The grand total", provider.prompts[1])

	def test_parallel_runs_one_call_per_field(self):
		provider = FakeProvider()
		(result, _), _ = self.run_extract("Parallel", provider)
		self.assertEqual(result, {"invoice_no": "INV-7", "total": "1,500.00"})
		self.assertEqual(len(provider.prompts), 2)

	def test_provider_errors_are_logged_once_and_fields_stay_empty(self):
		(result, confidence), log_error = self.run_extract("Per Field", FakeProvider(fail=True))
		self.assertEqual((result, confidence), ({"invoice_no": None, "total": None}, 0.0))
		log_error.assert_called_once()

	def test_strict_raises_when_the_ai_cannot_be_reached(self):
		with (
			patch.object(extractor, "get_provider", return_value=FakeProvider(fail=True)),
			patch.object(extractor.frappe, "get_cached_doc", return_value=NS(extraction_mode="Batch")),
			patch.object(extractor.frappe, "log_error"),
		):
			with self.assertRaises(ProviderError):
				extractor.extract("Invoice INV-7", RULES, strict=True)

	def test_rules_without_ai_hints_are_skipped(self):
		self.assertEqual(extractor.extract("text", [RULES[2], RULES[3]]), ({}, 0.0))
