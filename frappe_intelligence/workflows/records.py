"""The record a workflow fills in, on the desk: when the steps for a Target DocType are done, a new form
opens with their answers, for the user to check and save. Nothing is saved for them."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.utils.fields import writable_fieldname
from frappe_intelligence.workflows import steps


def form_action(conversation, workflow, finished, following) -> dict | None:
	"""A `new_doc` browser action once the last of the steps in a row for the same DocType is done."""
	doctype = finished.target_doctype
	if not doctype or (following and following.target_doctype == doctype) or conversation.channel != "Desk":
		return None
	if not frappe.has_permission(doctype, "create"):
		return None
	meta = frappe.get_meta(doctype)
	data = steps.collected(conversation)
	defaults = {
		fieldname: value
		for step in steps.ordered(workflow)
		if step.target_doctype == doctype
		for key, value in data.get(step.step_key, {}).items()
		if (fieldname := writable_fieldname(meta, key))
	}
	return {"type": "new_doc", "doctype": doctype, "defaults": defaults} if defaults else None


def opened_note(action: dict) -> str:
	return _("I opened a new {0} with these details. Check it and save it.").format(_(action["doctype"]))
