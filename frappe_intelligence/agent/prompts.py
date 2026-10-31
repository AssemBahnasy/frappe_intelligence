"""What the model is told. The system prompt stays the same between turns so providers can cache it;
anything that changes per message (page, language) is attached to the user's message instead."""

from __future__ import annotations

import frappe
from frappe.mcp.protocol import server_instructions

from frappe_intelligence.utils.language import language_rule

DEFAULT_NAME = "Assistant"

BEHAVIOUR = """You are {name}, the assistant inside this company's desk.
- Answer from the site's data: look records up with your tools before answering, and never invent records, numbers, names or field names.
- Before filtering or reading fields of a DocType you have not used yet, read its fields with get_doctype_schema.
- When a question is about the company's own procedures or policies, search the knowledge base first.
- Keep answers short. Show several records as a Markdown table.
- Link a record as [name](/app/<doctype in lowercase, spaces as dashes>/<name>) and a report as [report name](/app/query-report/<report name>). Only link records and reports your tools returned.
- If a tool reports an error, fix the arguments and try again, or explain what is missing."""

MODE_RULES = {
	"Ask": "You are in Ask mode: you can read data, open pages and prepare new forms, but you cannot save or change anything. If the user wants a change made, tell them to switch to Agent mode.",
	"Agent": """You are in Agent mode: you can create, update, submit, cancel and delete documents. Each change is shown to the user as a card and happens only after they confirm it.
- Prepare complete changes: read the DocType's fields first, fill every required field, and use exact names and values your tools returned.
- Say in one short sentence what you are about to change, then call the tool. Propose one change at a time unless the user asked for several.
- When a change is confirmed, report the result with a link to the record. When it is rejected, acknowledge it and do not propose it again unless asked.""",
}


def system_prompt(mode: str) -> str:
	settings = frappe.get_cached_doc("AI Settings")
	parts = [
		server_instructions(),
		BEHAVIOUR.format(name=settings.assistant_name or DEFAULT_NAME),
		MODE_RULES.get(mode, ""),
		settings.system_prompt or "",
	]
	return "\n\n".join(part for part in parts if part)


FILE_ONLY = "(The user sent only the attached file: use it for what the page they are on is for.)"


def with_context(text: str, context: dict | None) -> str:
	"""The user's message as the model sees it: page context and language rule first."""
	notes = [note for note in (page_note(context), language_rule(text)) if note]
	return "\n".join(f"<note>{note}</note>" for note in notes) + f"\n\n{text or FILE_ONLY}"


def page_note(context: dict | None) -> str:
	if not context:
		return ""
	doctype, name = context.get("doctype"), context.get("docname")
	if doctype and context.get("new"):
		return (
			f"The user has a new, unsaved {doctype} form open. Put the values for it straight into that "
			"form with fill_form (do not just list them); they review and save it."
		)
	if doctype and name:
		tab = f", on the {context['tab']} tab" if context.get("tab") else ""
		return f"The user has {doctype} {name} open{tab}."
	if doctype and context.get("list_filters"):
		return f"The user is viewing the {doctype} list filtered by {frappe.as_json(context['list_filters'], indent=None)}."
	if doctype:
		return f"The user is viewing the {doctype} list."
	if context.get("route"):
		return f"The user is on the desk page /{context['route']}."
	return ""
