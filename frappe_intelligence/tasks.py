"""Scheduled background tasks for frappe_intelligence."""

import frappe
from frappe.utils import add_days, now_datetime


def expire_old_sessions():
	"""Mark workflow conversations that have been idle for > 7 days as Abandoned.

	Runs daily via scheduler_events in hooks.py.
	"""
	cutoff = add_days(now_datetime(), -7)

	stale = frappe.db.get_all(
		"AI Conversation",
		filters={
			"mode": "Workflow",
			"status": "Active",
			"modified": ("<", cutoff),
		},
		pluck="name",
	)

	if not stale:
		return

	for name in stale:
		frappe.db.set_value("AI Conversation", name, "status", "Abandoned")

	frappe.db.commit()
	frappe.logger("frappe_intelligence").info(
		f"expire_old_sessions: marked {len(stale)} session(s) as Abandoned."
	)
