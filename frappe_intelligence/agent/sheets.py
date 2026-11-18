"""Sheets the assistant compiles: a table it built from the records it read, downloadable as Excel
or CSV. Who may take one follows Frappe's own export rules, decided by Frappe's functions at run time
(docs/panel/sheets.md)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.form.linked_with import get_parent_doctypes
from frappe.utils.xlsxutils import make_xlsx

from frappe_intelligence.agent.tools import registry

SHEET_TOOL = "export_sheet"
FORMATS = {"Excel": "xlsx", "CSV": "csv"}
MAX_ROWS = 5000
MAX_COLUMNS = 50


def read_doctypes(conversation, until_call_id: str | None = None) -> list[str]:
	"""The DocTypes whose records the conversation read, in order, up to the given call: from the tool
	calls it stores, each tool saying what it reads (AgentTool.reads), not from what the model says."""
	tools = registry()
	found: list[str] = []
	for call in _calls(conversation):
		if call.get("id") == until_call_id:
			break
		tool = tools.get(call.get("name"))
		doctype = tool.reads(call.get("arguments") or {}) if tool and tool.reads else None
		if doctype and doctype not in found:
			found.append(doctype)
	return found


def child_tables(doctypes: list[str]) -> dict[str, list[str]]:
	"""The child tables among the DocTypes, each with the DocTypes it sits in. Frappe gives a child
	table no rights of its own and checks its parent instead (frappe.permissions.has_child_permission)."""
	return get_parent_doctypes([doctype for doctype in doctypes if frappe.is_table(doctype)])


def export_rights(doctypes: list[str]) -> dict[str, bool]:
	"""The user's Export right on each DocType, as Frappe's report export checks it
	(frappe.desk.query_report.export_query); Export on one's own records only is not enough."""
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
