"""Scheduled background tasks for frappe_intelligence."""

import frappe
from frappe.utils import now_datetime, add_days


def expire_old_sessions():
    """Mark AI Agent Sessions that have been idle for > 7 days as Abandoned.

    Runs daily via scheduler_events in hooks.py.
    """
    cutoff = add_days(now_datetime(), -7)

    stale = frappe.db.get_all(
        "AI Agent Session",
        filters={
            "status": "Active",
            "modified": ("<", cutoff),
        },
        pluck="name",
    )

    if not stale:
        return

    for name in stale:
        frappe.db.set_value("AI Agent Session", name, "status", "Abandoned")

    frappe.db.commit()
    frappe.logger("frappe_intelligence").info(
        f"expire_old_sessions: marked {len(stale)} session(s) as Abandoned."
    )
