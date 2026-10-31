"""Chat endpoints: send a message, load and list conversations."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.agent import runs, transcript
from frappe_intelligence.documents import review
from frappe_intelligence.utils.access import agent_mode_allowed, ensure_assistant_access, limit_requests
from frappe_intelligence.utils.file_utils import validate_file_access
from frappe_intelligence.workflows import desk

MAX_MESSAGE_LENGTH = 4000
MAX_ATTACHMENTS = 3
CONVERSATION_LIST_LIMIT = 20
DESK_MODES = ("Ask", "Agent")


@frappe.whitelist(methods=["POST"])
@limit_requests
def send_message(
	message: str,
	conversation: str | None = None,
	context: dict | str | None = None,
	mode: str = "Ask",
	attachments: list | str | None = None,
) -> dict:
	"""Store `message` and answer it in the background. Follow the run on the `fi_assistant` realtime event.

	`attachments` are file URLs the user uploaded; they are read before the model answers. A change
	or reading still waiting for the user is set aside: they moved on without confirming it.
	"""
	ensure_assistant_access()
	files = _validated_attachments(attachments)
	text = _validated(message, allow_empty=bool(files))
	doc = _desk_conversation(conversation)
	runs.ensure_idle(doc)
	if doc.mode != "Workflow":
		doc.mode = _validated_mode(mode)
	doc.reject_pending()
	doc.add_user_message(text, frappe.parse_json(context) if context else None, files)
	run_id = runs.start(doc)
	return {"conversation": doc.name, "run_id": run_id}


@frappe.whitelist(methods=["POST"])
@limit_requests
def decide_proposal(conversation: str, call_id: str, approve: bool, values: dict | str | None = None) -> dict:
	"""Confirm or reject a proposed change, or confirm or discard a document reading (`values`: the
	fields as the user left them). Once none is left waiting, the answer continues in the background:
	approved changes run first, then the model reports back."""
	ensure_assistant_access()
	# Row lock: a double click cannot approve, and run, the same change twice.
	doc = _desk_conversation(conversation, for_update=True)
	runs.ensure_idle(doc)
	row = doc.decide(call_id, frappe.utils.sbool(approve))
	card = frappe.parse_json(row.preview or "{}")
	if row.approval == "Approved" and review.is_review(card):
		row.content = review.confirm(
			row.content, card, _validated_values(values), doc.name, doc.current_question()[1]
		)
	if doc.pending_proposals():
		doc.save()
		return {"run_id": None}
	return {"run_id": runs.start(doc)}


@frappe.whitelist(methods=["POST"])
def stop_message(conversation: str, run_id: str) -> dict:
	"""Ask the running answer to stop; the run ends with a `done` event marked `stopped`."""
	ensure_assistant_access()
	doc = frappe.get_doc("AI Conversation", conversation)
	doc.check_permission("write")
	runs.stop(doc, run_id)
	return {"ok": True}


@frappe.whitelist()
def get_conversation(name: str) -> dict:
	"""The conversation as the panel shows it, and `active_run` while an answer is being written."""
	ensure_assistant_access()
	doc = frappe.get_doc("AI Conversation", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"title": doc.title,
		"mode": doc.mode,
		"active_run": doc.active_run if runs.is_running(doc) else None,
		"turns": transcript.turns(doc),
		"workflow": desk.progress(doc) if doc.mode == "Workflow" else None,
	}


@frappe.whitelist(methods=["POST"])
def rate_reply(conversation: str, message: str, feedback: str | None = None) -> dict:
	"""Thumbs up or down on an answer; empty clears the rating."""
	ensure_assistant_access()
	if feedback not in (None, "", "Good", "Bad"):
		frappe.throw(_("Feedback must be Good or Bad."))
	doc = frappe.get_doc("AI Conversation", conversation)
	doc.check_permission("write")
	row = next((row for row in doc.messages if row.name == message and row.role == "assistant"), None)
	if not row:
		frappe.throw(_("Answer not found in this conversation."), frappe.DoesNotExistError)
	row.feedback = feedback or None
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def list_conversations(limit: int = CONVERSATION_LIST_LIMIT) -> list[dict]:
	ensure_assistant_access()
	return frappe.get_list(
		"AI Conversation",
		filters={"owner": frappe.session.user, "channel": "Desk"},
		fields=["name", "title", "mode", "modified"],
		order_by="modified desc",
		limit=min(int(limit), CONVERSATION_LIST_LIMIT),
	)


def _validated_mode(mode: str) -> str:
	if mode not in DESK_MODES:
		frappe.throw(_("Unknown mode: {0}").format(mode))
	if mode == "Agent" and not agent_mode_allowed():
		frappe.throw(_("Agent mode is turned off in AI Settings."), frappe.PermissionError)
	return mode


def _validated(message: str | None, allow_empty: bool = False) -> str:
	text = (message or "").strip()
	if not text and not allow_empty:
		frappe.throw(_("Message is empty."))
	if len(text) > MAX_MESSAGE_LENGTH:
		frappe.throw(_("Messages are limited to {0} characters.").format(MAX_MESSAGE_LENGTH))
	return text


def _validated_attachments(attachments: list | str | None) -> list[dict]:
	file_urls = frappe.parse_json(attachments) if attachments else []
	if not isinstance(file_urls, list) or not all(isinstance(url, str) for url in file_urls):
		frappe.throw(_("Attachments must be a list of file URLs."))
	if len(file_urls) > MAX_ATTACHMENTS:
		frappe.throw(_("Send at most {0} files with a message.").format(MAX_ATTACHMENTS))
	for file_url in file_urls:
		validate_file_access(file_url)
	return [
		{"file_url": url, "file_name": frappe.db.get_value("File", {"file_url": url}, "file_name") or url}
		for url in file_urls
	]


def _validated_values(values: dict | str | None) -> dict:
	values = frappe.parse_json(values) if values else {}
	if not isinstance(values, dict):
		frappe.throw(_("Values must be an object of field keys and values."))
	return values


def _desk_conversation(name: str | None, for_update: bool = False):
	"""The user's conversation to continue, or a new unsaved one."""
	if not name:
		return frappe.get_doc({"doctype": "AI Conversation", "mode": "Ask", "channel": "Desk"})
	doc = frappe.get_doc("AI Conversation", name, for_update=for_update)
	doc.check_permission("write")
	if doc.channel != "Desk":
		frappe.throw(_("This conversation cannot be continued here."))
	return doc
