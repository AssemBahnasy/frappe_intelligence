"""The export_report tool: who may export, and how the file reaches the user; over fakes."""

from __future__ import annotations

from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import frappe

from frappe_intelligence.agent.tools import AGENT, ASK, ToolError, execute, registry, reports

RECEIVABLE = frappe._dict(ref_doctype="Sales Invoice", report_type="Script Report")


class TestExportReport(TestCase):
	@contextmanager
	def site(self, report=RECEIVABLE, can_export=True, result=None):
		result = {"result": [[1]] * 3} if result is None else result
		with (
			patch.object(reports.frappe.db, "get_value", return_value=report),
			patch.object(reports.frappe.permissions, "can_export", return_value=can_export),
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
		self.assertEqual((action["delivery"], action["rows"]), ("open", None))

	def test_refused_without_the_export_right(self):
		with self.site(can_export=False) as run, self.assertRaises(ToolError) as raised:
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
