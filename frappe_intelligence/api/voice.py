"""Voice input in the assistant panel: the browser uploads a recording, this turns it into text in the
background, and the text goes into the message box for the user to check and send."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.utils import background, optional
from frappe_intelligence.utils.access import ensure_assistant_access, limit_requests

AUDIO_EXTENSIONS = (".webm", ".ogg", ".m4a", ".mp4", ".wav", ".mp3")  # assistant/voice.js records these


@frappe.whitelist(methods=["POST"])
@limit_requests
def transcribe(file_url: str) -> dict:
	"""`{"job": id}`; the text is the job's value (utils/background.py). It is deleted afterwards, so
	only a recording the user just uploaded: their own private audio File, attached to nothing."""
	ensure_assistant_access()
	if not optional.installed(optional.VOICE):
		frappe.throw(_("Voice input needs the transcription package, which is not installed on this server."))
	file = frappe.db.get_value(
		"File",
		{
			"file_url": file_url,
			"owner": frappe.session.user,
			"is_private": 1,
			"attached_to_doctype": ("is", "not set"),
		},
		"name",
	)
	if not file or not file_url.lower().endswith(AUDIO_EXTENSIONS):
		frappe.throw(_("Recording not found."), frappe.DoesNotExistError)
	return {"job": background.start("frappe_intelligence.documents.voice.transcribe_recording", file=file)}
