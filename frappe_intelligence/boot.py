"""What the desk needs at load time to show the assistant."""

import frappe
from frappe import _

from frappe_intelligence.agent import suggestions
from frappe_intelligence.documents import voice
from frappe_intelligence.utils import optional
from frappe_intelligence.utils.access import agent_mode_allowed, can_use_assistant, field_writer_allowed
from frappe_intelligence.workflows import desk
from frappe_intelligence.writer import text


def boot_session(bootinfo):
	if not can_use_assistant():
		return
	bootinfo.fi_assistant = {
		"name": frappe.get_cached_doc("AI Settings").assistant_name or _("Assistant"),
		"suggestions": suggestions.for_user(),
		"agent_mode": agent_mode_allowed(),
		"workflows": desk.startable(),
		# Field types that get Write with AI; empty when it is turned off.
		"field_writer": list(text.FIELD_TYPES) if field_writer_allowed() else [],
		# Voice input, when the transcription package is installed: the language it listens for.
		"voice": {"language": voice.language()} if optional.installed(optional.VOICE) else None,
	}
