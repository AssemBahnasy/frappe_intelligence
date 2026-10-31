"""Voice input from the assistant panel: a recording the browser uploaded becomes text, on this
server (documents/transcriber.py), and the recording is deleted."""

from __future__ import annotations

import frappe

from frappe_intelligence.documents.transcriber import transcribe
from frappe_intelligence.utils.file_utils import resolve_file_path


def transcribe_recording(file: str) -> str:
	"""Text of the user's recording (File name), in AI Settings → Voice Transcription Language, or the
	language spoken when that is empty."""
	file_url = frappe.db.get_value("File", file, "file_url")
	try:
		return transcribe(resolve_file_path(file_url), language=language() or None)
	finally:
		frappe.delete_doc("File", file, ignore_permissions=True)


def language() -> str:
	return frappe.get_cached_doc("AI Settings").voice_language or ""
