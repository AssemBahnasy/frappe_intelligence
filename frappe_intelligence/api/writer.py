"""Write with AI: the AI writes one long text field of the form the user has open. Nothing is
saved; the browser puts the text in the field and the user saves the form."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import strip_html

from frappe_intelligence.utils import background
from frappe_intelligence.utils.access import ensure_assistant_access, field_writer_allowed, limit_requests
from frappe_intelligence.writer import text

HIDDEN_TYPES = ("Password", "Attach", "Attach Image", "Signature", "Code", "JSON", "Geolocation")
MAX_INSTRUCTION = 2000
MAX_CURRENT = 10000
MAX_CONTEXT_FIELDS = 40
MAX_CONTEXT_VALUE = 300


@frappe.whitelist(methods=["POST"])
@limit_requests
def write_field(
	doctype: str,
	fieldname: str,
	instruction: str,
	current: str | None = None,
	context: dict | str | None = None,
	docname: str | None = None,
) -> dict:
	"""Write the field in the background: `{"job": id}`; the text is the job's value
	(utils/background.py). `context` is the form's other values, by field name; `docname` is
	omitted on a new form."""
	ensure_assistant_access()
	if not field_writer_allowed():
		frappe.throw(_("Write with AI is turned off in AI Settings."), frappe.PermissionError)
	df = _writable_field(doctype, fieldname, docname)
	instruction = (instruction or "").strip()
	if not instruction:
		frappe.throw(_("Describe what the field should say."))
	if len(instruction) > MAX_INSTRUCTION:
		frappe.throw(_("Keep the description under {0} characters.").format(MAX_INSTRUCTION))
	job = background.start(
		"frappe_intelligence.writer.text.write",
		doctype=_(doctype),
		label=_(df.label or df.fieldname),
		fieldtype=df.fieldtype,
		instruction=instruction,
		current=_plain(current, df)[:MAX_CURRENT],
		context=_context(doctype, context),
	)
	return {"job": job}


def _writable_field(doctype: str, fieldname: str, docname: str | None):
	if docname:
		frappe.has_permission(doctype, "write", doc=docname, throw=True)
	else:
		frappe.has_permission(doctype, "create", throw=True)
	meta = frappe.get_meta(doctype)
	df = meta.get_field(fieldname)
	if not df or df.fieldtype not in text.FIELD_TYPES or df.read_only:
		frappe.throw(_("Write with AI works on long text fields you can edit."))
	if df.permlevel not in meta.get_permlevel_access("write"):
		frappe.throw(_("You cannot edit this field."), frappe.PermissionError)
	return df


def _context(doctype: str, values: dict | str | None) -> list[tuple[str, str]]:
	"""`[(label, value)]` of the fields the user may read; anything else they sent is left out."""
	values = frappe.parse_json(values) if values else {}
	if not isinstance(values, dict):
		return []
	meta = frappe.get_meta(doctype)
	readable = meta.get_permlevel_access("read")
	context = []
	for fieldname, value in values.items():
		df = meta.get_field(fieldname)
		if not df or df.fieldtype in HIDDEN_TYPES or df.permlevel not in readable or value in (None, ""):
			continue
		context.append((_(df.label or df.fieldname), _plain(value, df)[:MAX_CONTEXT_VALUE]))
		if len(context) == MAX_CONTEXT_FIELDS:
			break
	return context


def _plain(value, df) -> str:
	value = "" if value is None else str(value)
	return strip_html(value).strip() if df.fieldtype == "Text Editor" else value.strip()
