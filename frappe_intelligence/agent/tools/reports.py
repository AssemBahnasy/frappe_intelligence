"""Find, run and export Frappe reports the user may open."""

from __future__ import annotations

import frappe
from frappe import _, _lt
from frappe.desk.query_report import run as run_query_report

from frappe_intelligence.agent.tools import AgentTool, ToolError

SEARCH_LIMIT = 20
ROW_LIMIT = 50
EXPORT_FORMATS = ("Excel", "CSV")
EXPORT_TYPES = ("Query Report", "Script Report")
# More rows than this: Frappe exports in the background and emails the user a link.
EMAIL_ROWS = 10_000


def search_reports(arguments: dict) -> list[dict]:
	query = arguments.get("query") or ""
	reports = frappe.get_list(
		"Report",
		filters={"disabled": 0, "name": ("like", f"%{query}%")},
		fields=["name", "ref_doctype", "report_type"],
		order_by="name",
		limit=SEARCH_LIMIT * 3,
	)
	permitted = [report for report in reports if frappe.has_permission(report.ref_doctype, "report")]
	return permitted[:SEARCH_LIMIT]


def run_report(arguments: dict) -> dict:
	result = run_query_report(arguments["report_name"], filters=arguments.get("filters") or {})
	if result.get("prepared_report"):
		raise ToolError(
			_("This report is prepared in the background. Ask the user to open it from the desk.")
		)

	columns = [column for column in result.get("columns") or [] if isinstance(column, dict)]
	rows = result.get("result") or []
	return {
		"columns": [column.get("label") or column.get("fieldname") for column in columns],
		"rows": [_row(row, columns) for row in rows[:ROW_LIMIT]],
		"total_rows": len(rows),
		"truncated": len(rows) > ROW_LIMIT,
		"message": result.get("message"),
	}


def export_report(arguments: dict) -> dict:
	"""A card for the panel to take a report away: download it (Frappe's Export), print it or save
	it as a PDF (the report page's own Print and PDF). Each shows only with the user's right on the
	report's DocType, as on the report page; here the rights are checked and the rows counted, and
	the browser runs Frappe's own code."""
	report_name = arguments["report_name"]
	file_format = arguments.get("file_format") or "Excel"
	if file_format not in EXPORT_FORMATS:
		raise ToolError(_("The format must be Excel or CSV."))
	report = frappe.db.get_value(
		"Report", {"name": report_name, "disabled": 0}, ["ref_doctype", "report_type"], as_dict=True
	)
	if not report:
		raise ToolError(_("Report {0} does not exist.").format(report_name))
	if report.report_type not in EXPORT_TYPES:
		raise ToolError(_("Only Query and Script reports can be exported from here."))
	can_export = bool(frappe.permissions.can_export(report.ref_doctype))
	can_print = frappe.has_permission(report.ref_doctype, "print")
	if not (can_export or can_print):
		raise ToolError(
			_("The user may not export or print {0}: their role has neither right on {1}.").format(
				report_name, report.ref_doctype
			)
		)

	filters = arguments.get("filters") or {}
	result = run_query_report(report_name, filters=dict(filters))
	prepared = bool(result.get("prepared_report"))
	rows = None if prepared else len(result.get("result") or [])
	if prepared:
		delivery = "open"
	elif not can_export:
		delivery = "print"
	else:
		delivery = "email" if rows > EMAIL_ROWS else "download"
	action = {
		"type": "export_report",
		"report_name": report_name,
		"filters": filters,
		"file_format": file_format,
		"rows": rows,
		"delivery": delivery,
		"can_export": can_export,
		"can_print": can_print and not prepared,
	}
	return {"action": action, "status": _status(action, report.ref_doctype)}


def _status(action: dict, ref_doctype: str) -> str:
	"""What the model is told the card offers, so its answer matches."""
	offers = {
		"open": "This report is prepared in the background: the card opens it, and the user exports or prints it there.",
		"print": (
			f"The user may not export {ref_doctype}, so there is no file to download; say so. "
			f"The card lets them print the {action['rows']} rows or save them as a PDF."
		),
		"email": f"{action['rows']} rows is too many to wait for: the card lets the user have Frappe email them the file.",
		"download": f"A card under your answer lets the user download {action['rows']} rows as {action['file_format']}.",
	}
	status = offers[action["delivery"]]
	if action["can_print"] and action["delivery"] != "print":
		status += " It can also print the report or save it as a PDF."
	return status


def _row(row, columns: list[dict]) -> list:
	if isinstance(row, dict):
		return [row.get(column.get("fieldname")) for column in columns]
	return list(row)


TOOLS = [
	AgentTool(
		name="search_reports",
		description="Find reports whose name contains the query, limited to reports the user may run.",
		parameters={"type": "object", "properties": {"query": {"type": "string"}}},
		run=search_reports,
		label=_lt("Searching reports"),
	),
	AgentTool(
		name="run_report",
		description=(
			f"Run a Query or Script report with filters (an object of filter name to value). "
			f"Returns the columns and the first {ROW_LIMIT} rows; `truncated` tells when there are more."
		),
		parameters={
			"type": "object",
			"properties": {"report_name": {"type": "string"}, "filters": {"type": "object"}},
			"required": ["report_name"],
		},
		run=run_report,
		label=_lt("Running {report_name}"),
	),
	AgentTool(
		name="export_report",
		description=(
			"Give the user a Query or Script report to take away: a card under your answer downloads "
			"it as Excel or CSV, prints it or saves it as a PDF, each as the user's rights allow, "
			"with the same filters as run_report. Use it whenever the user asks to export, download, "
			"print or get a report as a file or PDF; never paste the rows instead."
		),
		parameters={
			"type": "object",
			"properties": {
				"report_name": {"type": "string"},
				"filters": {"type": "object"},
				"file_format": {"type": "string", "enum": list(EXPORT_FORMATS)},
			},
			"required": ["report_name"],
		},
		run=export_report,
		label=_lt("Preparing the export of {report_name}"),
		browser_action=True,
	),
]
