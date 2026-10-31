"""Document review: reading, confirming the user's values, and how the panel shows it; no site needed."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_intelligence.agent import transcript
from frappe_intelligence.documents import review, templates

TEMPLATE = NS(
	name="Supplier Invoice",
	document_name="Supplier Invoice",
	document_type_key="supplier_invoice",
	model_preference="Heuristic",
	extraction_rules=[
		NS(field_key="bill_no", label="Bill No"),
		NS(field_key="due_date", label="Due Date"),
	],
)
CARD = {
	"kind": "review",
	"log": "LOG-1",
	"fields": [
		{"key": "bill_no", "label": "Bill No", "value": "GP-8841"},
		{"key": "due_date", "label": "Due Date", "value": ""},
	],
}


def patched(target: str, **kwargs):
	return patch(f"frappe_intelligence.documents.review.{target}", **kwargs)


class TestRead(TestCase):
	def read(self, template, values=None):
		with (
			patched("frappe.db", new=MagicMock(**{"get_value.return_value": "bill.pdf"})),
			patched("read_file_text", return_value="Bill GP-8841"),
			patched("templates.match", return_value=template),
			patched("templates.extract", return_value=(values or {}, 0.5)),
			patched("_log", return_value=NS(name="LOG-1")),
			patched("confidence_threshold", return_value=0.6),
		):
			return review.read("/private/files/bill.pdf")

	def test_without_a_template_the_model_reads_the_text(self):
		result = self.read(None)
		self.assertEqual((result["document"], result["text"]), ("bill.pdf", "Bill GP-8841"))
		self.assertNotIn("review", result)

	def test_a_matched_template_gives_every_field_to_review(self):
		result = self.read(TEMPLATE, {"bill_no": "GP-8841"})
		card = result.pop("review")
		self.assertEqual(result["template"], "Supplier Invoice")
		self.assertEqual([f["value"] for f in card["fields"]], ["GP-8841", ""])
		self.assertTrue(card["needs_review"])
		self.assertEqual(card["log"], "LOG-1")


class TestConfirm(TestCase):
	def confirm(self, values, can_write=True):
		log = MagicMock(document_template="Supplier Invoice", extracted_data='{"bill_no": "GP-8841"}')
		log.name = "LOG-1"
		context = {"doctype": "Purchase Invoice", "docname": "PI-1"}
		with (
			patched("frappe.get_doc", return_value=log),
			patched("frappe.has_permission", return_value=can_write),
			patched("_training_pair") as pair,
		):
			reading = '{"document": "bill.pdf", "template": "Supplier Invoice", "text": "Bill GP-8841"}'
			content = review.confirm(reading, CARD, values, "CONV-1", context)
		return json.loads(content), log, pair

	def test_the_users_values_are_what_the_model_gets(self):
		result, _, pair = self.confirm({"bill_no": "GP-8841", "due_date": " 30-11-2026 "})
		self.assertEqual(result["values"], {"bill_no": "GP-8841", "due_date": "30-11-2026"})
		self.assertEqual(result["labels"], {"bill_no": "Bill No", "due_date": "Due Date"})
		self.assertEqual(result["edited_by_user"], ["Due Date"])
		self.assertEqual(result["text"], "Bill GP-8841")
		self.assertLess(list(result).index("values"), list(result).index("text"))
		pair.assert_called_once()
		self.assertEqual(pair.call_args.args[1], {"bill_no": "GP-8841", "due_date": "30-11-2026"})

	def test_unchanged_values_keep_no_training_pair(self):
		result, _, pair = self.confirm({"bill_no": "GP-8841", "due_date": ""})
		self.assertNotIn("edited_by_user", result)
		pair.assert_not_called()

	def test_the_reading_is_linked_to_the_record_only_with_write_access(self):
		_, log, _ = self.confirm({}, can_write=True)
		log.db_set.assert_called_once_with(
			{"session": "CONV-1", "linked_doctype": "Purchase Invoice", "linked_docname": "PI-1"},
			update_modified=False,
		)
		_, log, _ = self.confirm({}, can_write=False)
		log.db_set.assert_called_once_with({"session": "CONV-1"}, update_modified=False)


class TestTemplates(TestCase):
	def test_both_fills_what_patterns_missed_with_the_ai(self):
		template = NS(**{**vars(TEMPLATE), "model_preference": "Both"})
		with (
			patch.object(templates.HeuristicExtractor, "extract", return_value=({"bill_no": "GP-8841"}, 1.0)),
			patch.object(templates.extractor, "extract", return_value=({"due_date": "30-11"}, 0.5)) as ai,
		):
			values, confidence = templates.extract("text", template)
		self.assertEqual(values, {"bill_no": "GP-8841", "due_date": "30-11"})
		self.assertEqual(confidence, 0.75)
		self.assertEqual([rule.field_key for rule in ai.call_args.args[1]], ["due_date"])


class TestTranscript(TestCase):
	def test_a_question_shows_its_files_and_the_reading_waits_for_review(self):
		file = {"file_url": "/private/files/bill.pdf", "file_name": "bill.pdf"}
		call = {"id": "r1", "name": "read_document", "arguments": file}
		rows = [
			frappe._dict(role="user", name="m1", content="", attachments=json.dumps([file]), creation="now"),
			frappe._dict(role="assistant", name="m2", content="", tool_calls=json.dumps([call])),
			frappe._dict(
				role="tool",
				name="m3",
				tool_name="read_document",
				tool_call_id="r1",
				content='{"text": "GP-8841"}',
				approval="Pending",
				preview=json.dumps(CARD),
				is_error=0,
			),
		]
		with (
			patch.object(transcript, "needs_approval", return_value=False),
			patch.object(transcript, "step_label", return_value="Reading bill.pdf"),
			patch.object(transcript, "registry", return_value={}),
		):
			[turn] = transcript.turns(NS(messages=rows))
		self.assertEqual(turn["attachments"], [file])
		self.assertEqual(turn["steps"], [{"label": "Reading bill.pdf", "status": "done"}])
		self.assertEqual(
			[(p["status"], p["preview"]["kind"]) for p in turn["proposals"]], [("pending", "review")]
		)


class TestReadTool(TestCase):
	def test_an_unreadable_file_tells_the_model_without_details(self):
		from frappe_intelligence.agent.tools import ToolError, documents

		with (
			patch.object(documents, "validate_file_access"),
			patch.object(
				documents.review, "read", side_effect=FileNotFoundError("/home/x/private/files/a.pdf")
			),
			patch.object(documents.frappe, "log_error") as log,
			patch.object(documents, "_", side_effect=lambda text: text),
		):
			with self.assertRaises(ToolError) as raised:
				documents.read_document({"file_url": "/private/files/a.pdf"})
		self.assertNotIn("/home", str(raised.exception))
		log.assert_called_once()

	def test_a_missing_ocr_package_is_named_so_the_user_knows(self):
		from frappe_intelligence.agent.tools import ToolError, documents
		from frappe_intelligence.utils.optional import MissingPackage

		with (
			patch.object(documents, "validate_file_access"),
			patch.object(documents.review, "read", side_effect=MissingPackage("needs the OCR package")),
		):
			with self.assertRaises(ToolError) as raised:
				documents.read_document({"file_url": "/private/files/photo.jpg"})
		self.assertEqual(str(raised.exception), "needs the OCR package")
