"""Sheets the assistant compiles from the records it read (agent/sheets.py): checking the user's
Export rights first, then a card to download the sheet."""

from __future__ import annotations

import frappe
from frappe import _, _lt

from frappe_intelligence.agent import sheets
from frappe_intelligence.agent.tools import AgentTool, ToolContext, ToolError


def check_export_rights(arguments: dict) -> dict:
	doctypes = [str(doctype) for doctype in arguments.get("doctypes") or []]
	unknown = [doctype for doctype in doctypes if not frappe.db.exists("DocType", doctype)]
	if unknown:
		raise ToolError(_("No such DocType: {0}. Search for its name first.").format(", ".join(unknown)))
	tables = sheets.child_tables(doctypes)
	rights = sheets.export_rights([doctype for doctype in doctypes if doctype not in tables])
	refused = [doctype for doctype, allowed in rights.items() if not allowed]
	out = {"export": rights}
	if tables:
		out["child_tables"] = {
			table: f"A table inside {', '.join(sorted(set(parents)))}, with no rights of its own: its rows come with the document you read it from."
			for table, parents in tables.items()
		}
	if refused:
		out["next"] = (
			f"The user may not export {', '.join(refused)}: tell them, read nothing, and offer to show the result in your answer instead."
		)
	elif tables:
		out["next"] = (
			"Read each child table through its document, and make sure that DocType was checked here "
			"(call check_export_rights with it if not). Then read the records and call export_sheet."
		)
	else:
		out["next"] = "The user may export all of them: read the records, then call export_sheet."
	return out


def export_sheet(arguments: dict, context: ToolContext) -> dict:
	title, columns, rows = sheets.validate_sheet(arguments)
	doctypes = sheets.read_doctypes(context.conversation, context.call_id)
	if not doctypes:
		raise ToolError(
			_(
				"A sheet is built only from records read in this conversation: read them with your tools first."
			)
		)
	sheets.ensure_exportable(doctypes)
	action = {
		"type": "export_sheet",
		"conversation": context.conversation.name,
		"call_id": context.call_id,
		"title": title,
		"columns": columns,
		"row_count": len(rows),
		"built_from": doctypes,
		"file_format": arguments.get("file_format") or "Excel",
	}
	return {
		"action": action,
		"status": f"A card under your answer lets the user download the sheet ({len(rows)} rows). Show the same rows as a table in your answer.",
	}


TOOLS = [
	AgentTool(
		name="check_export_rights",
		description=(
			"Whether the user may export each DocType (the Export right). Call it first whenever the "
			"user wants data you will compile as a file, with every DocType you plan to list, open or "
			"run a report on. Fields you take through a link or a child table come with that DocType. "
			"A child table has no right of its own: name the document you read it through."
		),
		parameters={
			"type": "object",
			"properties": {"doctypes": {"type": "array", "items": {"type": "string"}}},
			"required": ["doctypes"],
		},
		run=check_export_rights,
		label=_lt("Checking your Export rights"),
	),
	AgentTool(
		name="export_sheet",
		description=(
			"Give the user a table you compiled from records you read in this conversation as an Excel "
			"or CSV file: a download card under your answer. Use it only when no report gives the "
			"table (else export_report), after check_export_rights. Values must come from your tools; "
			f"at most {sheets.MAX_ROWS} rows and {sheets.MAX_COLUMNS} columns."
		),
		parameters={
			"type": "object",
			"properties": {
				"title": {"type": "string"},
				"columns": {"type": "array", "items": {"type": "string"}},
				"rows": {"type": "array", "items": {"type": "array"}},
				"file_format": {"type": "string", "enum": list(sheets.FORMATS)},
			},
			"required": ["title", "columns", "rows"],
		},
		run=export_sheet,
		label=_lt("Preparing the sheet"),
		browser_action=True,
		with_context=True,
	),
]
