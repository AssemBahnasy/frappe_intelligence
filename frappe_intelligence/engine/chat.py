"""Guided-workflow replies for every channel (desk, portal, WhatsApp).

Free chat on the desk runs through agent/loop.py; this module keeps the workflow
flow until it moves to workflows/ (see docs/architecture/README.md).
"""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.agent.tools.knowledge import knowledge_block
from frappe_intelligence.utils.language import language_rule

DEFAULT_SYSTEM = (
	"You are a helpful assistant integrated with a Frappe-based business application. "
	"Answer concisely and accurately."
)
CHANNEL_FLAGS = {"Desk": "allow_desk", "Portal": "allow_portal", "WhatsApp": "allow_whatsapp"}


def workflow_reply(text: str, channel: str, channel_id: str, workflow_key: str) -> dict:
	"""Answer `text` inside the guided workflow `workflow_key` for this channel user.

	1. Refuse when the workflow is inactive or not allowed on the channel.
	2. Scope gate: off-topic messages get the workflow's redirect, without a model call.
	3. Build the prompt from the current step and what has been collected.
	4. Call the model with the conversation history and save both turns.
	"""
	from frappe_intelligence.engine import scope as _scope
	from frappe_intelligence.engine import workflow as _wf

	if not _workflow_available(workflow_key, channel):
		return _reply(_("This workflow is not available here."))

	session = _wf.get_or_create_session(channel, channel_id, workflow_key)
	workflow_doc = _wf.get_workflow(session)

	if workflow_doc:
		in_scope, redirect = _scope.check_scope(text, workflow_doc)
		if not in_scope:
			return _record(session, text, redirect)

	step = _wf.get_current_step(session)
	if session.status == "Abandoned":
		return _record(
			session,
			text,
			_("This session was reset because the workflow was updated. Please start a new conversation."),
		)

	if step:
		collected = _wf.get_collected_for_step(session, step.step_key)
		instructions = _wf.build_step_prompt(step, collected, workflow_doc)
	elif workflow_doc and workflow_doc.completion_message:
		# Completed workflow with a fixed closing message: no model call.
		return _record(session, text, workflow_doc.completion_message)
	else:
		instructions = (workflow_doc and workflow_doc.scope_description) or (
			"The user's workflow is complete. Answer any follow-up questions within the scope of this service."
		)

	prompt = "\n\n".join(
		part
		for part in (
			language_rule(text),
			knowledge_block(text),
			instructions,
			f"<user_message>\n{text}\n</user_message>",
		)
		if part
	)
	reply, error = _ask_model(prompt, _wf.get_turn_history(session))
	if error:
		return _record(
			session, text, _("Could not reach the AI model ({0}). Please try again.").format(error)
		)
	return {
		**_record(session, text, reply or _("Sorry, I could not generate a reply. Please try rephrasing.")),
		"session": session.name,
	}


def _workflow_available(workflow_key: str, channel: str) -> bool:
	flags = frappe.db.get_value(
		"AI Workflow", workflow_key, ["is_active", CHANNEL_FLAGS[channel]], as_dict=True
	)
	return bool(flags and flags.is_active and flags[CHANNEL_FLAGS[channel]])


def _record(session, text: str, reply: str) -> dict:
	from frappe_intelligence.engine import workflow as _wf

	_wf.append_turn(session, "user", text)
	_wf.append_turn(session, "assistant", reply)
	return _reply(reply)


def _reply(text: str) -> dict:
	return {"reply": text, "action": None, "action_data": None}


def _ask_model(prompt: str, history: list[dict]) -> tuple[str | None, str | None]:
	"""One model turn without tools: `(text, error)`."""
	from frappe_intelligence.providers import Message, ProviderError, get_provider

	messages = [Message(role=turn["role"], content=turn["content"]) for turn in history]
	messages.append(Message(role="user", content=prompt))
	system = frappe.get_cached_doc("AI Settings").system_prompt or DEFAULT_SYSTEM
	try:
		reply = get_provider().complete(messages, system=system, on_text=_publish_chunk)
	except ProviderError as exc:
		return None, str(exc)
	finally:
		_publish_chunk("", done=True)
	return reply.text.strip() or None, None


def _publish_chunk(text: str, done: bool = False) -> None:
	frappe.publish_realtime("ai_stream_chunk", {"chunk": text, "done": done}, user=frappe.session.user)
