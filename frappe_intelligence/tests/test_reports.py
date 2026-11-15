"""Taking a report or a document away: export_report and print_document, who may use them, and
what the card offers; over fakes."""

from __future__ import annotations

from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import frappe

from frappe_intelligence.agent.tools import AGENT, ASK, ToolError, desk, execute, registry, reports

RECEIVABLE = frappe._dict(ref_doctype="Sales Invoice", report_type="Script Report")


class TestExportReport(TestCase):
	@contextmanager
	def site(self, report=RECEIVABLE, can_export=True, can_print=True, result=None):
		result = {"result": [[1]] * 3} if result is None else result
		with (
			patch.object(reports.frappe.db, "get_value", return_value=report),
			patch.object(reports.frappe.permissions, "can_export", return_value=can_export),
			patch.object(reports.frappe, "has_permission", return_value=can_print),
			patch.object(reports, "run_query_report", return_value=result) as run,
			patch.object(reports, "_", side_effect=lambda text: text),
		):
			yield run

	def export(self, **arguments):
		return reports.export_report({"report_name": "Accounts Receivable", **arguments})

	def test_a_card_to_download(self):
		filters = {"company": "Awesome Company"}
		with self.site() as run:
			action = self.export(filters=filters, file_format="CSV")["action"]
		self.assertEqual(action["type"], "export_report")
		self.assertEqual((action["rows"], action["delivery"], action["file_format"]), (3, "download", "CSV"))
		self.assertEqual(action["filters"], filters)
		run.assert_called_once_with("Accounts Receivable", filters=filters)

	def test_excel_by_default(self):
		with self.site():
			self.assertEqual(self.export()["action"]["file_format"], "Excel")

	def test_a_big_report_is_emailed(self):
		with self.site(result={"result": [[1]] * (reports.EMAIL_ROWS + 1)}):
			self.assertEqual(self.export()["action"]["delivery"], "email")

	def test_a_prepared_report_is_opened(self):
		with self.site(result={"prepared_report": True}):
			action = self.export()["action"]
		self.assertEqual((action["delivery"], action["rows"], action["can_print"]), ("open", None, False))

	def test_print_and_pdf_with_the_print_right(self):
		with self.site():
			action = self.export()["action"]
		self.assertEqual((action["can_export"], action["can_print"]), (True, True))
		with self.site(can_print=False):
			self.assertFalse(self.export()["action"]["can_print"])

	def test_print_only_without_the_export_right(self):
		with self.site(can_export=False):
			out = self.export()
		self.assertEqual(out["action"]["delivery"], "print")
		self.assertFalse(out["action"]["can_export"])
		self.assertIn("may not export Sales Invoice", out["status"])

	def test_refused_with_neither_right(self):
		with self.site(can_export=False, can_print=False) as run, self.assertRaises(ToolError) as raised:
			self.export()
		self.assertIn("Sales Invoice", str(raised.exception))
		run.assert_not_called()

	def test_refused_for_a_missing_report(self):
		with self.site(report=None), self.assertRaises(ToolError):
			self.export()

	def test_refused_for_a_report_builder_report(self):
		with self.site(report=frappe._dict(ref_doctype="ToDo", report_type="Report Builder")):
			with self.assertRaises(ToolError):
				self.export()

	def test_refused_for_another_format(self):
		with self.site(), self.assertRaises(ToolError):
			self.export(file_format="PDF")

	def test_the_card_reaches_the_panel_in_both_modes(self):
		tool = registry()["export_report"]
		self.assertEqual(tool.modes, frozenset({ASK, AGENT}))
		with self.site(), patch.object(reports.frappe.db, "savepoint"):
			outcome = execute("export_report", {"report_name": "Accounts Receivable"}, ASK)
		self.assertFalse(outcome.is_error)
		self.assertEqual(outcome.action["delivery"], "download")


class TestPrintDocument(TestCase):
	def print_view(self, rights=(True, True), exists=True):
		with (
			patch.object(desk.frappe, "has_permission", side_effect=rights) as has_permission,
			patch.object(desk.frappe.db, "exists", return_value=exists),
			patch.object(desk, "_", side_effect=lambda text: text),
		):
			return desk.print_document({"doctype": "Sales Invoice", "name": "SINV-1"}), has_permission

	def test_opens_the_print_view(self):
		out, has_permission = self.print_view()
		self.assertEqual(out["action"], {"type": "print_view", "doctype": "Sales Invoice", "name": "SINV-1"})
		has_permission.assert_called_with("Sales Invoice", "print", "SINV-1", throw=True)

	def test_needs_the_print_right_not_only_read(self):
		with self.assertRaises(frappe.PermissionError):
			self.print_view(rights=frappe.PermissionError)

	def test_a_missing_document(self):
		with self.assertRaises(ToolError):
			self.print_view(exists=False)

	def test_offered_in_both_modes(self):
		self.assertEqual(registry()["print_document"].modes, frozenset({ASK, AGENT}))
