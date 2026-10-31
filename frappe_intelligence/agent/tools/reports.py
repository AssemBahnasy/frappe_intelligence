"""Find and run Frappe reports the user may open."""

from __future__ import annotations

import frappe
from frappe import _, _lt
from frappe.desk.query_report import run as run_query_report

from frappe_intelligence.agent.tools import AgentTool, ToolError

SEARCH_LIMIT = 20
ROW_LIMIT = 50


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
]
