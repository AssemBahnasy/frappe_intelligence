"""The agent loop: model → tools → results → model, until the model answers in plain text.

Files sent with the question are read first. In Agent mode a change the model asks for becomes a
proposal, and a document that matches a template becomes a review: the turn pauses, and the next
run (after the user decides) applies the decision before calling the model again."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from frappe import _

from frappe_intelligence.agent import prompts
from frappe_intelligence.agent.tools import execute, needs_approval, propose, step_label, tools_for
from frappe_intelligence.providers import ProviderError, Reply, get_provider
from frappe_intelligence.providers.base import OnText

MAX_STEPS = 8
# Sent to the model, so kept in English; the transcript recognises it to show "stopped".
STOPPED_RESULT = "Stopped by the user before this ran."


class Stopped(Exception):
	"""The user pressed Stop."""


@dataclass
class Step:
	call_id: str
	tool: str
	label: str
	status: str  # running, done, failed, stopped


@dataclass
class Hooks:
	"""How the caller follows and controls a turn. All optional."""

	on_text: OnText | None = None
	on_step: Callable[[Step], None] | None = None
	should_stop: Callable[[], bool] = lambda: False
	# Called after each model turn and tool batch, e.g. to save progress.
	checkpoint: Callable[[], None] = lambda: None


@dataclass
class TurnResult:
	reply: str = ""
	actions: list[dict] = field(default_factory=list)
	steps: list[Step] = field(default_factory=list)
	error: str | None = None
	stopped: bool = False
	proposals: list[dict] = field(default_factory=list)  # changes and readings waiting for the user


def run_turn(conversation, hooks: Hooks | None = None) -> TurnResult:
	"""Answer the conversation's latest user message, calling tools as the model asks.

	The caller stores the user message first and saves the conversation afterwards.
	"""
	hooks = hooks or Hooks()
	text, context = conversation.current_question()
	provider = get_provider()
	specs = [tool.spec() for tool in tools_for(conversation.mode)] or None
	system = prompts.system_prompt(conversation.mode)
	result = TurnResult()

	try:
		_run_approved(conversation, hooks, result)
		_read_attachments(conversation, hooks, result)
		for _step in range(MAX_STEPS):
			if result.proposals:
				break
			_stop_if_asked(hooks)
			reply = _complete(provider, conversation, text, context, system, specs, hooks)
			conversation.add_reply(reply)
			hooks.checkpoint()
			if not reply.tool_calls:
				result.reply = reply.text or _empty_reply_text(reply.stop_reason)
				break
			_run_tools(conversation, reply, hooks, result)
			hooks.checkpoint()
			if result.proposals:
				result.reply = reply.text
				break
		else:
			result.reply = _("I stopped after {0} steps. Ask me to continue if you need more.").format(
				MAX_STEPS
			)
			conversation.add_error(result.reply)
	except Stopped:
		result.stopped = True
		conversation.add_stopped()
	except ProviderError as exc:
		result.error = str(exc)
		conversation.add_error(result.error)
	return result


def _complete(provider, conversation, text, context, system, specs, hooks: Hooks) -> Reply:
	"""One model turn. On Stop mid-answer, the text streamed so far is kept as the reply."""
	streamed: list[str] = []

	def relay(delta: str) -> None:
		streamed.append(delta)
		if hooks.on_text:
			hooks.on_text(delta)
		_stop_if_asked(hooks)

	try:
		return provider.complete(
			_with_context(conversation.provider_messages(), text, context),
			system=system,
			tools=specs,
			on_text=relay,
		)
	except Stopped:
		if streamed:
			conversation.add_reply(Reply(text="".join(streamed)))
		raise


def _run_tools(conversation, reply: Reply, hooks: Hooks, result: TurnResult) -> None:
	stopped = False
	for call in reply.tool_calls:
		# Every tool call needs a result, or providers reject the next turn.
		label = step_label(call.name, call.arguments)
		stopped = stopped or hooks.should_stop()
		if stopped:
			conversation.add_tool_result(call, STOPPED_RESULT, is_error=True)
			_record(result, hooks, Step(call.id, call.name, label, "stopped"))
			continue
		if needs_approval(call.name):
			_propose(conversation, call, result)
			continue
		_execute(conversation, call, label, hooks, result)
	if stopped:
		raise Stopped


def _execute(conversation, call, label: str, hooks: Hooks, result: TurnResult, row=None) -> None:
	"""Run a tool call and store its result; `row` is an approved proposal waiting for it."""
	_record(result, hooks, Step(call.id, call.name, label, "running"), announce_only=True)
	outcome = execute(call.name, call.arguments, conversation.mode)
	if row is not None:
		row.content, row.is_error = outcome.content, int(outcome.is_error)
	elif outcome.review:
		conversation.add_proposal(call, outcome.review, outcome.content)
		result.proposals.append({"call_id": call.id, "preview": outcome.review})
	else:
		conversation.add_tool_result(call, outcome.content, outcome.is_error)
	_record(result, hooks, Step(call.id, call.name, label, "failed" if outcome.is_error else "done"))
	if outcome.action:
		result.actions.append(outcome.action)


def _propose(conversation, call, result: TurnResult) -> None:
	"""An invalid change goes back to the model to fix; a valid one waits for the user."""
	outcome = propose(call.name, call.arguments, conversation.mode)
	if outcome.is_error:
		conversation.add_tool_result(call, outcome.content, is_error=True)
		return
	conversation.add_proposal(call, outcome.preview)
	result.proposals.append({"call_id": call.id, "preview": outcome.preview})


def _run_approved(conversation, hooks: Hooks, result: TurnResult) -> None:
	approved = conversation.approved_to_run()
	for row, call in approved:
		_execute(conversation, call, step_label(call.name, call.arguments), hooks, result, row)
	if approved:
		hooks.checkpoint()


def _read_attachments(conversation, hooks: Hooks, result: TurnResult) -> None:
	"""Files sent with the question are read before the model is called, so it always sees them."""
	calls = conversation.unread_attachments()
	if not calls:
		return
	_stop_if_asked(hooks)
	conversation.add_reply(Reply(tool_calls=calls, stop_reason="tool_calls"))
	for call in calls:
		_execute(conversation, call, step_label(call.name, call.arguments), hooks, result)
	hooks.checkpoint()


def _record(result: TurnResult, hooks: Hooks, step: Step, announce_only: bool = False) -> None:
	if not announce_only:
		result.steps.append(step)
	if hooks.on_step:
		hooks.on_step(step)


def _stop_if_asked(hooks: Hooks) -> None:
	if hooks.should_stop():
		raise Stopped


def _with_context(messages: list, text: str, context: dict | None) -> list:
	"""Attach the page and language notes to the current user message only."""
	index = max(i for i, message in enumerate(messages) if message.role == "user")
	current = messages[index]
	messages[index] = type(current)(**{**vars(current), "content": prompts.with_context(text, context)})
	return messages


def _empty_reply_text(stop_reason: str) -> str:
	if stop_reason == "refusal":
		return _("The AI declined to answer this request.")
	return _("The AI returned an empty answer. Please try rephrasing.")
