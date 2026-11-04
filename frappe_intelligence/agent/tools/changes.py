"""Changes the assistant prepares in Agent mode. Each is checked and shown as an approval card;
nothing runs until the user confirms (agent/loop.py, api/chat.decide_proposal)."""

from __future__ import annotations

import frappe
from frappe import _, _lt
from frappe.mcp import tools as mcp
from frappe.mcp.tools import documents
from frappe.model import table_fields
from frappe.utils import strip_html
from pydantic import ValidationError

from frappe_intelligence.agent.tools import AGENT_ONLY, AgentTool, ToolError
from frappe_intelligence.utils.access import agent_mode_refusal

# Never changed by the assistant, whatever AI Settings says: who can do what, and its own settings.
ALWAYS_EXCLUDED = frozenset(
	{
		"User",
		"Role",
		"Role Profile",
		"Has Role",
		"DocPerm",
		"Custom DocPerm",
		"User Permission",
		"System Settings",
		"AI Settings",
		"AI Conversation",
	}
)


def ensure_changeable(doctype: str) -> None:
	"""Checked when the card is built and again when the change runs: settings may change in between."""
	if refusal := agent_mode_refusal():
		raise ToolError(refusal)
	excluded = {row.excluded_doctype for row in frappe.get_cached_doc("AI Settings").agent_excluded_doctypes}
	if doctype in ALWAYS_EXCLUDED or doctype in excluded:
		raise ToolError(_("The assistant is not allowed to change {0}.").format(doctype))


def _validated(tool: mcp.Tool, arguments: dict) -> dict:
	"""The same argument check Frappe's MCP server applies, run before showing the card."""
	try:
		return tool.arguments.model_validate(arguments).model_dump()
	except ValidationError as exc:
		raise ToolError(mcp.validation_message(exc)) from exc


def _run_mcp(tool: mcp.Tool, arguments: dict):
	result = mcp.call({"name": tool.name, "arguments": arguments})
	if result["isError"]:
		raise ToolError(result["content"][0]["text"])
	return result["structuredContent"]


def _card(action: str, title: str, doctype: str, name: str | None = None, data: dict | None = None) -> dict:
	meta = frappe.get_meta(doctype)
	saved_as_draft = action == "create" and meta.is_submittable
	return {
		"action": action,
		"title": title,
		"doctype": doctype,
		"name": name,
		"fields": [_field(meta, key, value) for key, value in (data or {}).items()],
		"note": _("Saved as Draft. You submit it.")
		if saved_as_draft
		else _("Nothing is saved until you confirm."),
	}


def _field(meta, fieldname: str, value) -> dict:
	df = meta.get_field(fieldname)
	if df and df.fieldtype in table_fields:
		shown = _("{0} rows").format(len(value or []))
	elif df:
		shown = strip_html(str(frappe.format(value, df))).strip()
	else:
		shown = str(value)
	return {"label": _(df.label) if df else fieldname, "value": shown}


def _existing(doctype: str, name: str, permission: str):
	ensure_changeable(doctype)
	if not frappe.db.exists(doctype, name):
		raise ToolError(_("{0} {1} does not exist.").format(doctype, name))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission(permission)
	return doc


def preview_create(arguments: dict) -> dict:
	args = _validated(documents.CREATE_DOCUMENT, arguments)
	ensure_changeable(args["doctype"])
	frappe.has_permission(args["doctype"], "create", throw=True)
	return _card("create", _("Create {0}").format(_(args["doctype"])), args["doctype"], data=args["data"])


def run_create(arguments: dict) -> dict:
	ensure_changeable(arguments["doctype"])
	doc = _run_mcp(documents.CREATE_DOCUMENT, arguments)
	return {"created": doc["name"], "doctype": arguments["doctype"]}


def preview_update(arguments: dict) -> dict:
	args = _validated(documents.UPDATE_DOCUMENT, arguments)
	_existing(args["doctype"], args["name"], "write")
	title = _("Update {0} {1}").format(_(args["doctype"]), args["name"])
	return _card("update", title, args["doctype"], args["name"], args["data"])


def run_update(arguments: dict) -> dict:
	ensure_changeable(arguments["doctype"])
	_run_mcp(documents.UPDATE_DOCUMENT, arguments)
	return {"updated": arguments["name"], "doctype": arguments["doctype"]}


def preview_delete(arguments: dict) -> dict:
	args = _validated(documents.DELETE_DOCUMENT, arguments)
	_existing(args["doctype"], args["name"], "delete")
	title = _("Delete {0} {1}").format(_(args["doctype"]), args["name"])
	return _card("delete", title, args["doctype"], args["name"])


def run_delete(arguments: dict) -> dict:
	ensure_changeable(arguments["doctype"])
	_run_mcp(documents.DELETE_DOCUMENT, arguments)
	return {"deleted": arguments["name"], "doctype": arguments["doctype"]}


def _docstatus_change(action: str, docstatus: int, title, done: str):
	def preview(arguments: dict) -> dict:
		doc = _existing(arguments["doctype"], arguments["name"], action)
		if doc.docstatus != docstatus:
			raise ToolError(
				_("{0} {1} cannot be changed this way in its current state.").format(doc.doctype, doc.name)
			)
		return _card(action, str(title).format(_(doc.doctype), doc.name), doc.doctype, doc.name)

	def run(arguments: dict) -> dict:
		doc = _existing(arguments["doctype"], arguments["name"], action)
		getattr(doc, action)()
		return {done: doc.name, "doctype": doc.doctype}

	return preview, run


preview_submit, run_submit = _docstatus_change("submit", 0, _lt("Submit {0} {1}"), "submitted")
preview_cancel, run_cancel = _docstatus_change("cancel", 1, _lt("Cancel {0} {1}"), "cancelled")

DOCUMENT = {
	"type": "object",
	"properties": {"doctype": {"type": "string"}, "name": {"type": "string"}},
	"required": ["doctype", "name"],
}

TOOLS = [
	AgentTool(
		name="create_document",
		description=(
			"Create a document. The user sees the values and must confirm before it is saved. "
			"Read the DocType's fields first and fill every required one."
		),
		parameters=documents.CREATE_DOCUMENT.input_schema,
		run=run_create,
		preview=preview_create,
		label=_lt("Creating {doctype}"),
		modes=AGENT_ONLY,
	),
	AgentTool(
		name="update_document",
		description="Change fields of an existing document. The user must confirm first.",
		parameters=documents.UPDATE_DOCUMENT.input_schema,
		run=run_update,
		preview=preview_update,
		label=_lt("Updating {doctype} {name}"),
		modes=AGENT_ONLY,
	),
	AgentTool(
		name="delete_document",
		description="Delete a document. The user must confirm first.",
		parameters=documents.DELETE_DOCUMENT.input_schema,
		run=run_delete,
		preview=preview_delete,
		label=_lt("Deleting {doctype} {name}"),
		modes=AGENT_ONLY,
	),
	AgentTool(
		name="submit_document",
		description="Submit a draft of a submittable DocType. The user must confirm first.",
		parameters=DOCUMENT,
		run=run_submit,
		preview=preview_submit,
		label=_lt("Submitting {doctype} {name}"),
		modes=AGENT_ONLY,
	),
	AgentTool(
		name="cancel_document",
		description="Cancel a submitted document. The user must confirm first.",
		parameters=DOCUMENT,
		run=run_cancel,
		preview=preview_cancel,
		label=_lt("Cancelling {doctype} {name}"),
		modes=AGENT_ONLY,
	),
]
