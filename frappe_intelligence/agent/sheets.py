"""Sheets the assistant compiles: a table it built from the records it read, downloadable as Excel
or CSV. The rows stay in the conversation, in the export_sheet call's arguments; the file is made by
Frappe's own builders on each download. Taking one away needs the Export right on every DocType the
conversation read (docs/panel/sheets.md)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils.xlsxutils import make_xlsx

SHEET_TOOL = "export_sheet"
FORMATS = {"Excel": "xlsx", "CSV": "csv"}
MAX_ROWS = 5000
MAX_COLUMNS = 50
# Tools that read records, and the argument naming their DocType.
DOCTYPE_READS = {"list_documents": "doctype", "get_document": "doctype", "count_documents": "doctype"}
REPORT_READS = {"run_report", "export_report"}


def read_doctypes(conversation, until_call_id: str | None = None) -> list[str]:
	"""The DocTypes whose records the conversation read, in order, up to the given call: from the
	tool calls it stores, not from what the model says."""
	found: list[str] = []
	for call in _calls(conversation):
		if call.get("id") == until_call_id:
			break
		doctype = _doctype_read(call)
		if doctype and doctype not in found:
			found.append(doctype)
	return found


def _doctype_read(call: dict) -> str | None:
	arguments = call.get("arguments") or {}
	if call.get("name") in DOCTYPE_READS:
		return arguments.get(DOCTYPE_READS[call["name"]])
	if call.get("name") in REPORT_READS and arguments.get("report_name"):
		return frappe.db.get_value("Report", arguments["report_name"], "ref_doctype")
	return None


def export_rights(doctypes: list[str]) -> dict[str, bool]:
	"""The user's Export right on each DocType, as the desk's Export buttons check it."""
	return {doctype: bool(frappe.permissions.can_export(doctype)) for doctype in doctypes}


def ensure_exportable(doctypes: list[str]) -> None:
	if refused := [doctype for doctype, allowed in export_rights(doctypes).items() if not allowed]:
		raise frappe.PermissionError(
			_("You are not allowed to export {0}, which this sheet was built from.").format(
				", ".join(_(doctype) for doctype in refused)
			)
		)


def validate_sheet(arguments: dict) -> tuple[str, list[str], list[list]]:
	title = (arguments.get("title") or "").strip()
	columns = [str(column) for column in arguments.get("columns") or []]
	rows = arguments.get("rows") or []
	if not title:
		raise frappe.ValidationError(_("A sheet needs a title."))
	if not columns or len(columns) > MAX_COLUMNS:
		raise frappe.ValidationError(_("A sheet needs between 1 and {0} columns.").format(MAX_COLUMNS))
	if not rows or len(rows) > MAX_ROWS:
		raise frappe.ValidationError(
			_("A sheet needs between 1 and {0} rows. A bigger one should be a report.").format(MAX_ROWS)
		)
	if any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
		raise frappe.ValidationError(_("Each row needs one value per column."))
	return title, columns, rows


def sheet_arguments(conversation, call_id: str) -> dict:
	for call in _calls(conversation):
		if call.get("id") == call_id and call.get("name") == SHEET_TOOL:
			return call.get("arguments") or {}
	raise frappe.DoesNotExistError(_("This sheet is no longer in the conversation."))


def sheet_file(conversation, call_id: str, file_format: str) -> tuple[str, str, bytes]:
	"""(title, extension, content), after checking the Export rights again."""
	if file_format not in FORMATS:
		frappe.throw(_("The format must be Excel or CSV."))
	ensure_exportable(read_doctypes(conversation, call_id))
	title, columns, rows = validate_sheet(sheet_arguments(conversation, call_id))
	data = [columns, *rows]
	if file_format == "CSV":
		from frappe.desk.utils import get_csv_bytes

		return title, "csv", get_csv_bytes(data, {})
	return title, "xlsx", make_xlsx(data, title).getvalue()


def _calls(conversation):
	for row in conversation.messages:
		if row.role == "assistant" and row.tool_calls:
			yield from frappe.parse_json(row.tool_calls)
