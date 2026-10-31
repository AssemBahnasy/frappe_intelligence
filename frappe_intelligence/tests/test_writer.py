"""Write with AI: which fields may be written, what the model reads, and the background job, over
fakes; no site needed."""

from __future__ import annotations

from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_intelligence.api import writer as api
from frappe_intelligence.providers import ProviderError, Reply
from frappe_intelligence.writer import text

FIELDS = {
	"customer_details": NS(
		fieldname="customer_details", label="Customer Details", fieldtype="Text", read_only=0, permlevel=0
	),
	"customer_name": NS(
		fieldname="customer_name", label="Customer Name", fieldtype="Data", read_only=0, permlevel=0
	),
	"primary_address": NS(
		fieldname="primary_address", label="Primary Address", fieldtype="Text", read_only=1, permlevel=0
	),
	"credit_note": NS(
		fieldname="credit_note", label="Credit Note", fieldtype="Small Text", read_only=0, permlevel=1
	),
	"api_key": NS(fieldname="api_key", label="API Key", fieldtype="Password", read_only=0, permlevel=0),
	"notes": NS(fieldname="notes", label="Notes", fieldtype="Text Editor", read_only=0, permlevel=0),
}


def meta(levels=(0,)):
	return MagicMock(
		**{"get_field.side_effect": FIELDS.get, "get_permlevel_access.return_value": list(levels)}
	)


def throw(message, exc=frappe.ValidationError, *args, **kwargs):
	raise exc(message)


def untranslated(module):
	return patch.object(module, "_", side_effect=lambda value: value)


class TestWritableField(TestCase):
	def field(self, fieldname, docname=None, levels=(0,)):
		with (
			untranslated(api),
			patch.object(api.frappe, "has_permission") as has_permission,
			patch.object(api.frappe, "throw", side_effect=throw),
			patch.object(api.frappe, "get_meta", return_value=meta(levels)),
		):
			df = api._writable_field("Customer", fieldname, docname)
		return df, has_permission

	def test_an_editable_long_text_field_on_a_new_form_needs_create_permission(self):
		df, has_permission = self.field("customer_details")
		self.assertEqual(df.fieldname, "customer_details")
		has_permission.assert_called_once_with("Customer", "create", throw=True)

	def test_a_saved_record_needs_write_permission_on_it(self):
		_df, has_permission = self.field("customer_details", docname="CUST-1")
		has_permission.assert_called_once_with("Customer", "write", doc="CUST-1", throw=True)

	def test_other_fields_are_refused(self):
		for fieldname in ("customer_name", "primary_address", "missing"):
			with self.assertRaises(frappe.ValidationError):
				self.field(fieldname)
		with self.assertRaises(frappe.PermissionError):
			self.field("credit_note")
		self.assertEqual(self.field("credit_note", levels=(0, 1))[0].fieldname, "credit_note")


class TestContext(TestCase):
	def test_only_readable_fields_reach_the_model_by_label(self):
		values = {
			"customer_name": "Al Waha Clinics",
			"api_key": "secret",
			"credit_note": "level 1",
			"notes": "<p>Six <b>branches</b></p>",
			"unknown": "x",
			"customer_details": "",
		}
		with untranslated(api), patch.object(api.frappe, "get_meta", return_value=meta()):
			context = api._context("Customer", values)
		self.assertEqual(context, [("Customer Name", "Al Waha Clinics"), ("Notes", "Six branches")])

	def test_values_are_cut(self):
		with untranslated(api), patch.object(api.frappe, "get_meta", return_value=meta()):
			[(_label, value)] = api._context("Customer", {"customer_name": "x" * 1000})
		self.assertEqual(len(value), api.MAX_CONTEXT_VALUE)


class TestText(TestCase):
	def test_the_prompt_has_the_form_the_values_the_current_text_and_the_request(self):
		with patch.object(text, "language_rule", return_value="Reply only in Arabic."):
			prompt = text.prompt(
				"Customer", "Customer Details", "Make it formal", "old text", [("Customer Name", "Al Waha")]
			)
		self.assertIn("Form: Customer\nField: Customer Details", prompt)
		self.assertIn("- Customer Name: Al Waha", prompt)
		self.assertIn("---\nold text\n---", prompt)
		self.assertTrue(prompt.endswith("Make it formal\n\n<note>Reply only in Arabic.</note>"))

	def test_fences_and_quotes_around_the_text_are_removed(self):
		self.assertEqual(
			text._unwrap('```\n"Al Waha Clinics is a clinic chain."\n```'),
			"Al Waha Clinics is a clinic chain.",
		)
		self.assertEqual(text._unwrap("It's fine."), "It's fine.")
		self.assertEqual(text._unwrap("“Six branches in Riyadh.”"), "Six branches in Riyadh.")

	def test_rich_fields_may_use_lists_plain_ones_may_not(self):
		provider = MagicMock(**{"complete.return_value": Reply(text="Done.")})
		with (
			patch.object(text, "get_provider", return_value=provider),
			patch.object(text.frappe, "get_cached_doc", return_value=NS(system_prompt="")),
			patch.object(text, "language_rule", return_value=""),
		):
			text.write("ToDo", "Description", "Text Editor", "three points", "", [])
			rich = provider.complete.call_args.kwargs["system"]
			text.write("Customer", "Details", "Text", "intro", "", [])
			plain = provider.complete.call_args.kwargs["system"]
		self.assertIn(text.RICH, rich)
		self.assertIn(text.PLAIN, plain)

	def test_the_job_keeps_the_result_for_the_user_and_tells_the_browser(self):
		request = dict(
			doctype="Customer", label="Details", fieldtype="Text", instruction="x", current="", context=[]
		)
		for outcome, expected in (
			({"return_value": "Written."}, {"text": "Written."}),
			({"side_effect": ProviderError("offline")}, {"error": "offline"}),
		):
			cache = MagicMock()
			with (
				patch.object(text, "write", **outcome),
				patch("frappe_intelligence.writer.text.frappe.cache", new=cache),
				patch.object(text.frappe, "publish_realtime") as publish,
				patch("frappe_intelligence.writer.text.frappe.session", new=NS(user="a@example.com")),
			):
				text.run("JOB1", **request)
			cache.set_value.assert_called_once_with(
				"fi_field_writer:a@example.com:JOB1", expected, expires_in_sec=600
			)
			publish.assert_called_once_with(
				"fi_field_writer", {"job": "JOB1", **expected}, user="a@example.com"
			)
