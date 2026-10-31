"""One turn of a guided workflow, the same on every channel (desk panel, portal, WhatsApp).

1. Topic gate: a plainly off-topic message gets the workflow's redirect, without AI (scope.py).
2. The answer is read into the current step's fields (answers.py). A message that answered nothing
   and shares no words with the workflow gets the redirect too.
3. A complete step moves the conversation on; on the desk the record's form opens (records.py).
4. The AI writes the reply: brief thanks, then the next question. The last step is closed without
   AI: the Completion Message, or a summary of the answers (a model tends to ask again instead).

The caller stores the user's message first and saves the conversation afterwards.
"""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.agent.loop import Hooks, Stopped, TurnResult, complete, with_current_message
from frappe_intelligence.agent.tools.knowledge import knowledge_block
from frappe_intelligence.documents.reader import read_file_text
from frappe_intelligence.providers import ProviderError, Reply, get_provider
from frappe_intelligence.utils.language import language_rule
from frappe_intelligence.workflows import answers, records, scope, steps

CHANNEL_FLAGS = {"Desk": "allow_desk", "Portal": "allow_portal", "WhatsApp": "allow_whatsapp"}
DOCUMENT_LIMIT = 4000
DEFAULT_SYSTEM = "You are a helpful assistant inside a Frappe business application."
# Sent to the model, so kept in English.
RULES = """You guide the user through the workflow "{title}", one step at a time.
- Ask only for what is still needed, in one or two short, friendly sentences.
- If the user asks about this process, answer briefly, then ask for what is still needed.
- Never invent values, and never say anything was saved or submitted."""
FILE_ONLY = "(The user sent only an attached file.)"


def available(workflow_key: str | None, channel: str) -> bool:
	flag = CHANNEL_FLAGS.get(channel)
	if not (flag and workflow_key):
		return False
	values = frappe.db.get_value("AI Workflow", workflow_key, ["is_active", flag], as_dict=True)
	return bool(values and values.is_active and values[flag])


def start(conversation, workflow) -> None:
	"""Put a new conversation on the workflow and ask the first step's question, without AI."""
	step = steps.begin(conversation, workflow)
	conversation.mode = "Workflow"
	conversation.title = workflow.title
	conversation.add_fixed_reply(
		question(conversation, step)
		if step
		else workflow.completion_message or _("This workflow has no steps yet.")
	)


def question(conversation, step) -> str:
	"""The step's own question, or a request for what it still needs."""
	if step.prompt_to_user:
		return step.prompt_to_user
	labels = steps.fields(step)
	needed = [labels[key] for key in steps.missing(conversation, step)] or list(labels.values())
	return _("Please tell me: {0}").format(", ".join(needed)) if needed else steps.label(step)


def run_turn(conversation, hooks: Hooks | None = None) -> TurnResult:
	hooks = hooks or Hooks()
	result = TurnResult()
	text, _context = conversation.current_question()
	if not available(conversation.workflow, conversation.channel):
		return _fixed(conversation, result, _("This workflow is not available here."))
	workflow = frappe.get_doc("AI Workflow", conversation.workflow)
	if conversation.status == "Paused":
		conversation.status = "Active"
	step = steps.current(conversation, workflow)
	if conversation.status == "Abandoned":
		return _fixed(
			conversation,
			result,
			_(
				"This workflow was changed after this conversation started, so it cannot continue. Please start it again."
			),
		)
	if scope.is_off_topic(text, workflow):
		return _redirect(conversation, workflow, step, result)

	moved, refusal = False, None
	if step:
		labels = steps.fields(step)
		# Every field is filled only when the completion check refused them: the user is correcting.
		needed = {key: labels[key] for key in steps.missing(conversation, step)} or labels
		try:
			found = answers.read(text, needed, _asked(conversation), _attached_text(conversation))
		except ProviderError as exc:
			return _failed(conversation, result, exc)
		if not found and labels and not scope.is_related(text, workflow, step):
			return _redirect(conversation, workflow, step, result)
		steps.collect(conversation, step, found)
		if not steps.missing(conversation, step):
			refusal = steps.refused(conversation, step)
			if not refusal:
				following = steps.advance(conversation, workflow)
				if action := records.form_action(conversation, workflow, step, following):
					result.actions.append(action)
				step, moved = following, True
	hooks.checkpoint()

	note = records.opened_note(result.actions[0]) if result.actions else ""
	if moved and not step:
		closing = workflow.completion_message or _summary(conversation, workflow)
		return _fixed(conversation, result, "\n\n".join(filter(None, [closing, note])))
	try:
		reply = _write(conversation, workflow, step, text, moved, refusal, hooks)
	except Stopped:
		result.stopped = True
		conversation.add_stopped()
		return result
	except ProviderError as exc:
		return _failed(conversation, result, exc)
	if note and hooks.on_text:
		hooks.on_text(f"\n\n{note}")
	written = reply.text.strip() or (question(conversation, step) if step else "")
	result.reply = "\n\n".join(filter(None, [written, note]))
	conversation.add_reply(Reply(text=result.reply))
	return result


def instructions(conversation, workflow, step, moved: bool = False, refusal: str | None = None) -> str:
	"""What the model is told about the workflow's state this turn."""
	if not step:
		details = "\n".join(
			f"- {answer['label']}: {answer['value']}" for answer in steps.summary(conversation, workflow)
		)
		return (
			"## All steps are complete\nAnswer follow-up questions within the mandate; ask for nothing "
			f"else. The answers given:\n{details}"
		)
	number, total = steps.position(workflow, step)
	return step_instructions(step, steps.values(conversation, step), number, total, moved, refusal)


def step_instructions(
	step,
	given: dict,
	number: int | None = None,
	total: int | None = None,
	moved: bool = False,
	refusal: str | None = None,
) -> str:
	"""The current step for the model: its question, what it has and what it still needs."""
	labels = steps.fields(step)
	counter = f" {number} of {total}" if number else ""
	lines = [f"## Current step{counter}: {steps.label(step)}"]
	if step.prompt_to_user:
		lines.append(f"Its question: {step.prompt_to_user}")
	if moved:
		lines.append(
			"The user has just completed the previous step: thank them in a few words, then ask this step's question."
		)
	if refusal:
		lines.append(f"The answers did not pass this step's check: {refusal} Ask the user to correct them.")
	have = [f"- {label}: {given[key]}" for key, label in labels.items() if given.get(key)]
	need = [f"- {label}" for key, label in labels.items() if not given.get(key)]
	if have:
		lines += ["### Already collected", *have]
	if need:
		lines += ["### Still needed from the user", *need, "Ask for these, and for nothing else."]
	return "\n".join(lines)


def _write(conversation, workflow, step, text: str, moved: bool, refusal: str | None, hooks: Hooks) -> Reply:
	packs = [row.pack for row in workflow.knowledge_packs or []]
	system = "\n\n".join(
		part
		for part in (
			frappe.get_cached_doc("AI Settings").system_prompt or DEFAULT_SYSTEM,
			RULES.format(title=workflow.title),
			f"## Your mandate\n{workflow.scope_description}" if workflow.scope_description else "",
			instructions(conversation, workflow, step, moved, refusal),
			knowledge_block(text, packs) if text else "",
		)
		if part
	)
	content = f"<note>{language_rule(text)}</note>\n\n{text or FILE_ONLY}"
	messages = with_current_message(conversation.provider_messages(), content)
	return complete(get_provider(), conversation, messages, system, None, hooks)


def _summary(conversation, workflow) -> str:
	answers = "\n".join(
		f"- {answer['label']}: {answer['value']}" for answer in steps.summary(conversation, workflow)
	)
	return "\n\n".join(filter(None, [_("Thank you, that's everything. Your answers:"), answers]))


def _redirect(conversation, workflow, step, result: TurnResult) -> TurnResult:
	reply = " ".join(filter(None, [scope.redirect(workflow), question(conversation, step) if step else ""]))
	return _fixed(conversation, result, reply, off_topic=True)


def _failed(conversation, result: TurnResult, error: ProviderError) -> TurnResult:
	result.error = str(error)
	conversation.add_error(result.error)
	return result


def _fixed(conversation, result: TurnResult, text: str, off_topic: bool = False) -> TurnResult:
	conversation.add_fixed_reply(text, off_topic)
	result.reply = text
	return result


def _asked(conversation) -> str:
	"""The question the user is answering: the last reply before their message."""
	rows = conversation.messages
	last_user = max(i for i, row in enumerate(rows) if row.role == "user")
	return next(
		(
			row.content
			for row in reversed(rows[:last_user])
			if row.role == "assistant" and row.content and not row.is_error
		),
		"",
	)


def _attached_text(conversation) -> str:
	row = next(row for row in reversed(conversation.messages) if row.role == "user")
	texts = []
	for file in frappe.parse_json(row.attachments) if row.attachments else []:
		try:
			texts.append(read_file_text(file["file_url"]))
		except OSError, ValueError, ImportError:
			frappe.log_error(f"Workflow could not read {file['file_url']}")
	return "\n\n".join(texts)[:DOCUMENT_LIMIT]
