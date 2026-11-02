"""The tutorial page (docs/tutorial/): marking a topic done."""

from __future__ import annotations

import frappe

from frappe_intelligence.tutorial import progress
from frappe_intelligence.utils.access import ensure_assistant_access


@frappe.whitelist(methods=["POST"])
def set_done(topic: str, done: bool = True) -> list[str]:
	"""Marks one of the user's tutorial topics done or not yet; returns the topics now done."""
	ensure_assistant_access()
	return progress.set_done(topic, bool(frappe.utils.cint(done)))
