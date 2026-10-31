"""What the desk needs at load time to show the assistant."""

import frappe
from frappe import _

from frappe_intelligence.agent import suggestions
from frappe_intelligence.utils.access import agent_mode_allowed, can_use_assistant


def boot_session(bootinfo):
	if not can_use_assistant():
		return
	bootinfo.fi_assistant = {
		"name": frappe.get_cached_doc("AI Settings").assistant_name or _("Assistant"),
		"suggestions": suggestions.for_user(),
		"agent_mode": agent_mode_allowed(),
	}
