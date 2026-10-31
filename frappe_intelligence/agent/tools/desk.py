"""Actions the browser performs for the user: open a page, a form or a new document, or draw a chart."""

from __future__ import annotations

import frappe
from frappe import _, _lt

from frappe_intelligence.agent.tools import AgentTool, ToolError

CHART_TYPES = ("bar", "line", "pie", "percentage", "donut")
CHART_LABEL_LIMIT = 100
CHART_DATASET_LIMIT = 8


def _action(action: dict, note: str) -> dict:
	return {"action": action, "status": note}


def navigate(arguments: dict) -> dict:
	route = (arguments.get("route") or "").strip().lstrip("/")
	if not route.startswith("app/") or "//" in route or ":" in route:
		raise ToolError(_("Only desk routes that start with /app/ can be opened."))
	return _action({"type": "set_route", "route": f"/{route}"}, "The page is opening for the user.")


def open_document(arguments: dict) -> dict:
	doctype, name = arguments["doctype"], arguments["name"]
	# DocType permission first, so a missing record reveals nothing to users who cannot read it.
	frappe.has_permission(doctype, "read", throw=True)
	if not frappe.db.exists(doctype, name):
		raise ToolError(_("{0} {1} does not exist.").format(doctype, name))
	frappe.has_permission(doctype, "read", name, throw=True)
	return _action(
		{"type": "open_form", "doctype": doctype, "name": name}, "The form is opening for the user."
	)


def new_document(arguments: dict) -> dict:
	doctype = arguments["doctype"]
	frappe.has_permission(doctype, "create", throw=True)
	return _action(
		{"type": "new_doc", "doctype": doctype, "defaults": arguments.get("defaults") or {}},
		"A new form is opening for the user to review and save.",
	)


def show_chart(arguments: dict) -> dict:
	chart_type = arguments.get("type") or "bar"
	labels = [str(label) for label in arguments.get("labels") or []]
	datasets = arguments.get("datasets") or []
	if chart_type not in CHART_TYPES:
		raise ToolError(_("Chart type must be one of: {0}").format(", ".join(CHART_TYPES)))
	if not labels or len(labels) > CHART_LABEL_LIMIT:
		raise ToolError(_("A chart needs between 1 and {0} labels.").format(CHART_LABEL_LIMIT))
	if not datasets or len(datasets) > CHART_DATASET_LIMIT:
		raise ToolError(_("A chart needs between 1 and {0} datasets.").format(CHART_DATASET_LIMIT))
	for dataset in datasets:
		values = dataset.get("values") or []
		if len(values) != len(labels) or not all(isinstance(value, int | float) for value in values):
			raise ToolError(_("Each dataset needs one number per label."))
	chart = {
		"type": "chart",
		"title": arguments.get("title") or "",
		"chart_type": chart_type,
		"labels": labels,
		"datasets": [{"name": d.get("name") or "", "values": d["values"]} for d in datasets],
	}
	return _action(chart, "The chart is shown under your answer.")


DOCUMENT = {"doctype": {"type": "string"}, "name": {"type": "string"}}

TOOLS = [
	AgentTool(
		name="navigate",
		description="Open a desk page for the user, for example /app/sales-invoice?status=Unpaid.",
		parameters={"type": "object", "properties": {"route": {"type": "string"}}, "required": ["route"]},
		run=navigate,
		label=_lt("Opening a page"),
		browser_action=True,
	),
	AgentTool(
		name="open_document",
		description="Open an existing document's form for the user.",
		parameters={"type": "object", "properties": DOCUMENT, "required": ["doctype", "name"]},
		run=open_document,
		label=_lt("Opening {doctype} {name}"),
		browser_action=True,
	),
	AgentTool(
		name="new_document",
		description=(
			"Open a new, unsaved form with the given field values filled in. "
			"The user reviews and saves it; nothing is saved by this tool."
		),
		parameters={
			"type": "object",
			"properties": {"doctype": {"type": "string"}, "defaults": {"type": "object"}},
			"required": ["doctype"],
		},
		run=new_document,
		label=_lt("Opening a new {doctype}"),
		browser_action=True,
	),
	AgentTool(
		name="show_chart",
		description="Draw a chart under your answer. Each dataset has a name and one number per label.",
		parameters={
			"type": "object",
			"properties": {
				"title": {"type": "string"},
				"type": {"type": "string", "enum": list(CHART_TYPES)},
				"labels": {"type": "array", "items": {"type": "string"}},
				"datasets": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"name": {"type": "string"},
							"values": {"type": "array", "items": {"type": "number"}},
						},
						"required": ["values"],
					},
				},
			},
			"required": ["labels", "datasets"],
		},
		run=show_chart,
		label=_lt("Drawing a chart"),
		browser_action=True,
	),
]
