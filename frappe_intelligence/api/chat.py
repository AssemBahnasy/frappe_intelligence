"""Chat endpoints: send a message, load and list conversations."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.agent import runs, transcript
from frappe_intelligence.agent.loop import Hooks, run_turn
from frappe_intelligence.engine.chat import workflow_reply
from frappe_intelligence.utils.access import agent_mode_allowed, ensure_assistant_access, limit_requests

MAX_MESSAGE_LENGTH = 4000
CONVERSATION_LIST_LIMIT = 20
DESK_MODES = ("Ask", "Agent")


@frappe.whitelist(methods=["POST"])
@limit_requests
def send_message(
	message: str,
	conversation: str | None = None,
	context: dict | str | None = None,
	mode: str = "Ask",
) -> dict:
	"""Store `message` and answer it in the background. Follow the run on the `fi_assistant` realtime event.

	A change still waiting for approval is rejected: the user moved on without confirming it.
	"""
	ensure_assistant_access()
	text = _validated(message)
	doc = _desk_conversation(conversation)
	runs.ensure_idle(doc)
	doc.mode = _validated_mode(mode)
	doc.reject_pending()
	doc.add_user_message(text, frappe.parse_json(context) if context else None)
	run_id = runs.start(doc)
	return {"conversation": doc.name, "run_id": run_id}


@frappe.whitelist(methods=["POST"])
@limit_requests
def decide_proposal(conversation: str, call_id: str, approve: bool) -> dict:
	"""Confirm or reject a proposed change. Once none is left waiting, the answer continues in the
	background: approved changes run first, then the model reports back."""
	ensure_assistant_access()
	# Row lock: a double click cannot approve, and run, the same change twice.
	doc = _desk_conversation(conversation, for_update=True)
	runs.ensure_idle(doc)
	doc.decide(call_id, frappe.utils.sbool(approve))
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
		filters={"owner": frappe.session.user, "channel": "Desk", "mode": ("!=", "Workflow")},
		fields=["name", "title", "mode", "modified"],
		order_by="modified desc",
		limit=min(int(limit), CONVERSATION_LIST_LIMIT),
	)


@frappe.whitelist()
@limit_requests
def handle_widget_input(
	input_type: str,
	file_url: str | None = None,
	text_input: str | None = None,
	doctype: str | None = None,
	docname: str | None = None,
	audio_pending: int = 0,
	widget_mode: str = "global",
	chat_mode: str = "ask",
	workflow_key: str | None = None,
) -> dict:
	"""Entry point of the current widget; the new panel calls send_message instead."""
	if audio_pending:
		return {"status": "pending", "reply": _("Upload in progress…")}
	ensure_assistant_access()

	if input_type == "file":
		from frappe_intelligence.api.documents import process_widget_file

		return process_widget_file(file_url, doctype, docname, workflow_key)

	if input_type == "voice":
		from frappe_intelligence.documents.transcriber import transcribe
		from frappe_intelligence.utils.file_utils import resolve_file_path, validate_file_access

		validate_file_access(file_url)
		language = frappe.get_cached_doc("AI Settings").voice_language or None
		transcript = transcribe(resolve_file_path(file_url), language=language)
		reply = _widget_reply(transcript, chat_mode, workflow_key, doctype, docname) if transcript else {}
		return {"transcript": transcript, **_legacy_reply(reply.get("reply", ""))}

	if input_type == "text":
		return _widget_reply(_validated(text_input), chat_mode, workflow_key, doctype, docname)

	frappe.throw(_("Unknown input_type '{0}'. Expected: file, voice, text.").format(input_type))


def _validated_mode(mode: str) -> str:
	if mode not in DESK_MODES:
		frappe.throw(_("Unknown mode: {0}").format(mode))
	if mode == "Agent" and not agent_mode_allowed():
		frappe.throw(_("Agent mode is turned off in AI Settings."), frappe.PermissionError)
	return mode


def _validated(message: str | None) -> str:
	text = (message or "").strip()
	if not text:
		frappe.throw(_("Message is empty."))
	if len(text) > MAX_MESSAGE_LENGTH:
		frappe.throw(_("Messages are limited to {0} characters.").format(MAX_MESSAGE_LENGTH))
	return text


def _desk_conversation(name: str | None, for_update: bool = False):
	"""The user's conversation to continue, or a new unsaved one."""
	if not name:
		return frappe.get_doc({"doctype": "AI Conversation", "mode": "Ask", "channel": "Desk"})
	doc = frappe.get_doc("AI Conversation", name, for_update=for_update)
	doc.check_permission("write")
	if doc.channel != "Desk" or doc.mode == "Workflow":
		frappe.throw(_("This conversation cannot be continued here."))
	return doc


def _widget_reply(text, chat_mode, workflow_key, doctype, docname) -> dict:
	if chat_mode == "agent" and workflow_key:
		return workflow_reply(text, "Desk", frappe.session.user, workflow_key)

	latest = frappe.get_all(
		"AI Conversation",
		filters={"owner": frappe.session.user, "channel": "Desk", "mode": "Ask"},
		order_by="modified desc",
		pluck="name",
		limit=1,
	)
	doc = _desk_conversation(latest[0] if latest else None)
	runs.ensure_idle(doc)
	doc.add_user_message(text, {"doctype": doctype, "docname": docname} if doctype else None)
	try:
		result = run_turn(doc, Hooks(on_text=_stream_chunk))
	finally:
		_stream_chunk("", done=True)
	doc.save()
	return _legacy_reply(result.reply or result.error or "")


def _legacy_reply(reply: str) -> dict:
	return {"reply": reply, "action": None, "action_data": None}


def _stream_chunk(text: str, done: bool = False) -> None:
	frappe.publish_realtime("ai_stream_chunk", {"chunk": text, "done": done}, user=frappe.session.user)
