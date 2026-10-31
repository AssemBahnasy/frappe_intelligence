"""Workflow conversations on the portal and WhatsApp, found by the channel's own id (the portal user,
the phone number). Their users are not desk users, so these conversations are saved as the system."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.workflows import turn


def session(channel: str, channel_id: str, workflow_key: str | None):
	"""The open conversation of this channel user on the workflow, or a new one on its first step."""
	name = frappe.db.get_value(
		"AI Conversation",
		{
			"mode": "Workflow",
			"channel": channel,
			"channel_id": channel_id,
			"workflow": workflow_key,
			"status": ("in", ("Active", "Paused")),
		},
		"name",
		order_by="modified desc",
	)
	if name:
		return frappe.get_doc("AI Conversation", name)
	doc = frappe.get_doc(
		{"doctype": "AI Conversation", "mode": "Workflow", "channel": channel, "channel_id": channel_id}
	)
	if workflow_key and frappe.db.exists("AI Workflow", workflow_key):
		turn.start(doc, frappe.get_doc("AI Workflow", workflow_key))
	doc.insert(ignore_permissions=True)
	return doc


def reply(text: str, channel: str, channel_id: str, workflow_key: str | None) -> dict:
	"""Answer `text` in the channel user's workflow conversation; the reply is returned, not streamed."""
	if not turn.available(workflow_key, channel):
		return _reply(_("This workflow is not available here."))
	doc = session(channel, channel_id, workflow_key)
	doc.add_user_message(text)
	result = turn.run_turn(doc)
	doc.save(ignore_permissions=True)
	return {**_reply(result.reply or result.error or ""), "session": doc.name}


def _reply(text: str) -> dict:
	return {"reply": text, "action": None, "action_data": None}
