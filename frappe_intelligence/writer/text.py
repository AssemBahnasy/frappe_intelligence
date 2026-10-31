"""The text for one field, written by the AI; api/writer.py runs it as a background job
(utils/background.py)."""

from __future__ import annotations

import re

import frappe
from frappe import _

from frappe_intelligence.providers import Message, ProviderError, get_provider
from frappe_intelligence.utils.language import language_rule

# Sent to the model, so kept in English.
SYSTEM = """You write the text of one field in a form of a business application.
- Return only the text for the field: no introduction, no quotes, no explanation.
- Use only facts from the user's request, the form's values and the field's current text. Never invent names, numbers or dates."""
PLAIN = "- Plain text: no Markdown, no headings."
RICH = "- Short paragraphs; simple Markdown lists when they help. No headings."
FIELD_TYPES = ("Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor")
RICH_TYPES = ("Text Editor", "Markdown Editor")
QUOTE_PAIRS = {('"', '"'), ("'", "'"), ("“", "”"), ("«", "»")}


def write(doctype: str, label: str, fieldtype: str, instruction: str, current: str, context: list) -> str:
	settings = frappe.get_cached_doc("AI Settings")
	system = "\n".join(filter(None, [SYSTEM, RICH if fieldtype in RICH_TYPES else PLAIN]))
	system = "\n\n".join(filter(None, [settings.system_prompt, system]))
	reply = get_provider().complete(
		[Message(role="user", content=prompt(doctype, label, instruction, current, context))], system=system
	)
	text = _unwrap(reply.text)
	if not text:
		raise ProviderError(_("The AI returned no text. Please describe it differently."))
	return text


def prompt(doctype: str, label: str, instruction: str, current: str, context: list) -> str:
	values = "\n".join(f"- {name}: {value}" for name, value in context)
	parts = [
		f"Form: {doctype}\nField: {label}",
		f"Other values on the form:\n{values}" if values else "",
		f"The field's current text:\n---\n{current}\n---" if current else "",
		f"What the user wants:\n{instruction}",
		f"<note>{language_rule(instruction)}</note>",
	]
	return "\n\n".join(part for part in parts if part)


def _unwrap(text: str) -> str:
	"""Models sometimes wrap the text in a code fence or quotes."""
	text = re.sub(r"^```\w*\n?|\n?```$", "", (text or "").strip()).strip()
	if len(text) > 1 and (text[0], text[-1]) in QUOTE_PAIRS:
		text = text[1:-1].strip()
	return text
