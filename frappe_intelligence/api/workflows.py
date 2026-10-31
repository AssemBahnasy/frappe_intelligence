"""Guided workflows in the assistant panel: start one, or leave it to come back later. Answers go
through chat.send_message like any message."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.agent import runs
from frappe_intelligence.utils.access import ensure_assistant_access, limit_requests
from frappe_intelligence.workflows import turn


@frappe.whitelist(methods=["POST"])
@limit_requests
def start_workflow(workflow: str) -> dict:
	"""A new conversation on the workflow's first step, its question already asked."""
	ensure_assistant_access()
	if not turn.available(workflow, "Desk"):
		frappe.throw(_("This workflow is not available here."), frappe.PermissionError)
	doc = frappe.get_doc({"doctype": "AI Conversation", "channel": "Desk"})
	turn.start(doc, frappe.get_doc("AI Workflow", workflow))
	doc.insert()
	return {"conversation": doc.name}


@frappe.whitelist(methods=["POST"])
def exit_workflow(conversation: str) -> dict:
	"""Pause the workflow; it stays in History and continues from the same step when the user answers."""
	ensure_assistant_access()
	doc = frappe.get_doc("AI Conversation", conversation, for_update=True)
	doc.check_permission("write")
	if doc.channel != "Desk" or doc.mode != "Workflow":
		frappe.throw(_("This conversation is not a guided workflow."))
	runs.ensure_idle(doc)
	if doc.status == "Active":
		doc.status = "Paused"
		doc.save()
	return {"ok": True}
