"""Sheets the assistant compiles: what the conversation read, the Export rights checked before,
when the card is made and at each download, and the file; over fakes."""

from __future__ import annotations

import io
import json
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import frappe
from openpyxl import load_workbook

from frappe_intelligence.agent import sheets
from frappe_intelligence.agent.tools import AGENT, ASK, ToolContext, ToolError, execute, registry
from frappe_intelligence.agent.tools import sheets as sheet_tools

SHEET = {
	"title": "Sales against target",
	"columns": ["Sales Person", "Sales"],
	"rows": [["Omar", 134500], ["=HYPERLINK(1)", 72300]],
}


def conversation(*calls):
	"""A conversation whose assistant rows made these tool calls, in order."""
	rows = [
		frappe._dict(role="assistant", tool_calls=json.dumps([{"id": f"c{i}", **call}]))
		for i, call in enumerate(calls)
	]
	return frappe._dict(name="conv-1", messages=[frappe._dict(role="user"), *rows])


READ_INVOICES = {"name": "list_documents", "arguments": {"doctype": "Sales Invoice"}}
READ_PERSON = {"name": "get_document", "arguments": {"doctype": "Sales Person", "name": "Omar"}}
SHEET_CALL = {"name": "export_sheet", "arguments": SHEET}


@contextmanager
def rights(**allowed):
	with patch.object(
		sheets.frappe.permissions, "can_export", side_effect=lambda doctype: allowed.get(doctype, True)
	):
		yield


class TestReadDoctypes(TestCase):
	def test_from_the_stored_calls_in_order_once_each(self):
		doc = conversation(READ_INVOICES, READ_PERSON, READ_INVOICES, SHEET_CALL)
		self.assertEqual(sheets.read_doctypes(doc, "c3"), ["Sales Invoice", "Sales Person"])

	def test_only_calls_before_the_sheet(self):
		doc = conversation(READ_INVOICES, SHEET_CALL, READ_PERSON)
		self.assertEqual(sheets.read_doctypes(doc, "c1"), ["Sales Invoice"])

	def test_fields_through_links_and_child_tables_come_with_the_listed_doctype(self):
		# As in Frappe's Report view export: the Export right on the listed DocType covers them.
		fields = ["name", "allocated_to.full_name as assignee", "`tabHas Role`.role"]
		doc = conversation({"name": "list_documents", "arguments": {"doctype": "ToDo", "fields": fields}})
		self.assertEqual(sheets.read_doctypes(doc), ["ToDo"])

	def test_tools_that_return_no_records_count_nothing(self):
		doc = conversation(
			{"name": "get_doctype_schema", "arguments": {"doctype": "Sales Invoice"}},
			{"name": "search_doctypes", "arguments": {"query": "invoice"}},
		)
		self.assertEqual(sheets.read_doctypes(doc), [])

	def test_each_tool_that_returns_records_says_which(self):
		tools = registry()
		readers = {name for name, tool in tools.items() if tool.reads}
		self.assertEqual(
			readers, {"list_documents", "get_document", "count_documents", "run_report", "export_report"}
		)

	def test_a_report_counts_as_its_doctype(self):
		doc = conversation({"name": "run_report", "arguments": {"report_name": "Accounts Receivable"}})
		with patch.object(sheets.frappe.db, "get_value", return_value="Sales Invoice"):
			self.assertEqual(sheets.read_doctypes(doc), ["Sales Invoice"])


class TestCheckExportRights(TestCase):
	def check(self, doctypes, **allowed):
		with rights(**allowed), patch.object(sheet_tools.frappe.db, "exists", return_value=True):
			return sheet_tools.check_export_rights({"doctypes": doctypes})

	def test_each_doctype(self):
		out = self.check(["Sales Invoice", "Sales Person"], **{"Sales Invoice": False})
		self.assertEqual(out["export"], {"Sales Invoice": False, "Sales Person": True})
		self.assertIn("read nothing", out["next"])

	def test_all_allowed(self):
		self.assertIn("export_sheet", self.check(["Sales Person"])["next"])

	def test_a_child_table_is_not_refused_but_sent_to_its_parent(self):
		# Frappe gives a child table no rights of its own, so can_export would always refuse it.
		out = self.check(["Has Role", "User"], **{"Has Role": False})
		self.assertEqual(out["export"], {"User": True})
		self.assertIn("User", out["child_tables"]["Has Role"])
		self.assertNotIn("read nothing", out["next"])


class TestExportSheet(TestCase):
	def export(self, doc, call_id, **allowed):
		with rights(**allowed), patch.object(sheets, "_", side_effect=lambda text: text):
			return sheet_tools.export_sheet(SHEET, ToolContext(doc, call_id))

	def test_a_card_built_from_what_was_read(self):
		action = self.export(conversation(READ_INVOICES, READ_PERSON, SHEET_CALL), "c2")["action"]
		self.assertEqual(action["built_from"], ["Sales Invoice", "Sales Person"])
		self.assertEqual(
			(action["conversation"], action["call_id"], action["row_count"]), ("conv-1", "c2", 2)
		)
		self.assertNotIn("rows", action)

	def test_refused_without_export_on_one_doctype(self):
		doc = conversation(READ_INVOICES, READ_PERSON, SHEET_CALL)
		with self.assertRaises(frappe.PermissionError) as raised:
			self.export(doc, "c2", **{"Sales Invoice": False})
		self.assertIn("Sales Invoice", str(raised.exception))

	def test_refused_when_nothing_was_read(self):
		with self.assertRaises(ToolError):
			self.export(conversation(SHEET_CALL), "c0")

	def test_rows_must_match_the_columns(self):
		with (
			patch.object(sheets, "_", side_effect=lambda text: text),
			self.assertRaises(frappe.ValidationError),
		):
			sheets.validate_sheet({**SHEET, "rows": [["only one"]]})

	def test_the_tool_gets_its_context_in_both_modes(self):
		tool = registry()["export_sheet"]
		self.assertTrue(tool.with_context)
		self.assertEqual(tool.modes, frozenset({ASK, AGENT}))
		doc = conversation(READ_INVOICES, SHEET_CALL)
		with rights(), patch.object(sheets.frappe.db, "savepoint"):
			outcome = execute("export_sheet", SHEET, ASK, ToolContext(doc, "c1"))
		self.assertFalse(outcome.is_error, outcome.content)
		self.assertEqual(outcome.action["call_id"], "c1")


class TestSheetFile(TestCase):
	doc = conversation(READ_INVOICES, SHEET_CALL)

	def test_excel_from_the_stored_rows(self):
		with rights():
			title, extension, content = sheets.sheet_file(self.doc, "c1", "Excel")
		self.assertEqual((title, extension), ("Sales against target", "xlsx"))
		cells = [[cell.value for cell in row] for row in load_workbook(io.BytesIO(content)).active.rows]
		self.assertEqual(cells[0], ["Sales Person", "Sales"])
		self.assertEqual(cells[1], ["Omar", 134500])
		# Text that looks like a formula stays text (Frappe's make_xlsx).
		self.assertEqual(cells[2][0], "=HYPERLINK(1)")
		self.assertEqual(load_workbook(io.BytesIO(content)).active["A3"].data_type, "s")

	def test_csv(self):
		with rights():
			_, extension, content = sheets.sheet_file(self.doc, "c1", "CSV")
		self.assertEqual(extension, "csv")
		self.assertTrue(content.decode().startswith("Sales Person,Sales"))

	def test_rights_checked_again_at_download(self):
		with rights(**{"Sales Invoice": False}), patch.object(sheets, "_", side_effect=lambda text: text):
			with self.assertRaises(frappe.PermissionError):
				sheets.sheet_file(self.doc, "c1", "Excel")

	def test_only_a_sheet_call(self):
		with rights(), patch.object(sheets, "_", side_effect=lambda text: text):
			with self.assertRaises(frappe.DoesNotExistError):
				sheets.sheet_file(self.doc, "c0", "Excel")
