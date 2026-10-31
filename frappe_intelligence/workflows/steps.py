"""The step machine: which step a workflow conversation is on, what it has collected, where it goes next.

The state lives on the AI Conversation (`workflow`, `current_step`, `collected_data`, `status`).
Nothing here saves it; the caller does, once per turn.
"""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.utils.callables import is_app_method

FINISHED = ("Completed", "Abandoned")


def ordered(workflow) -> list:
	return sorted(workflow.steps or [], key=lambda step: step.step_order or 0)


def find(workflow, step_key: str | None):
	return next((step for step in workflow.steps or [] if step_key and step.step_key == step_key), None)


def begin(conversation, workflow):
	"""Put the conversation on the workflow's first step; returns that step."""
	first = next(iter(ordered(workflow)), None)
	conversation.workflow = workflow.name
	conversation.current_step = first.step_key if first else ""
	conversation.collected_data = "{}"
	conversation.status = "Active" if first else "Completed"
	return first


def current(conversation, workflow):
	"""The step being answered, or None once the workflow is finished.

	A step removed from the workflow since the conversation started ends the conversation
	(status Abandoned): its answers no longer fit the workflow.
	"""
	if conversation.status in FINISHED or not conversation.current_step:
		return None
	step = find(workflow, conversation.current_step)
	if not step:
		conversation.status = "Abandoned"
	return step


def fields(step) -> dict[str, str]:
	"""`{field key: label}` the step asks for (AI Workflow Step → Required Fields)."""
	data = frappe.parse_json(step.required_fields) if step.required_fields else {}
	if isinstance(data, list):
		return {key: key for key in data if isinstance(key, str)}
	return {key: label or key for key, label in data.items()} if isinstance(data, dict) else {}


def collected(conversation) -> dict[str, dict]:
	"""`{step key: {field key: value}}`."""
	data = frappe.parse_json(conversation.collected_data) if conversation.collected_data else {}
	return data if isinstance(data, dict) else {}


def values(conversation, step) -> dict:
	return collected(conversation).get(step.step_key, {})


def missing(conversation, step) -> list[str]:
	given = values(conversation, step)
	return [key for key in fields(step) if not given.get(key)]


def collect(conversation, step, answers: dict) -> None:
	"""Keep the answers to the step's own fields; a new answer replaces an earlier one."""
	known = fields(step)
	data = collected(conversation)
	data[step.step_key] = {
		**data.get(step.step_key, {}),
		**{key: value for key, value in answers.items() if key in known and value},
	}
	conversation.collected_data = frappe.as_json(data, indent=None)


def refused(conversation, step) -> str | None:
	"""Why the step's Completion Check keeps the user on it, or None when it lets them move on.

	The check is a dotted path to `check(values, collected)` in an installed app. It returns True to
	move on, or False or a message for the user to stay on the step.
	"""
	method = (step.completion_check or "").strip()
	if not method:
		return None
	if not is_app_method(method):
		frappe.log_error(f"Workflow completion check blocked: {method!r} is not in an installed app")
		return None
	try:
		outcome = frappe.get_attr(method)(
			values=values(conversation, step), collected=collected(conversation)
		)
	except Exception:
		frappe.log_error(f"Workflow completion check {method} failed")
		return _("These answers could not be checked. Please check them and send them again.")
	if outcome and not isinstance(outcome, str):
		return None
	return (
		outcome
		if isinstance(outcome, str) and outcome
		else _("These answers did not pass this step's check.")
	)


def advance(conversation, workflow):
	"""Move to the next step: the step's Next Step, else the next by order. None when the workflow is done."""
	step = find(workflow, conversation.current_step)
	following = _following(workflow, step) if step else None
	conversation.current_step = following.step_key if following else ""
	if not following:
		conversation.status = "Completed"
	return following


def position(workflow, step) -> tuple[int, int]:
	"""`(number of the step, number of steps)`, by order."""
	steps = ordered(workflow)
	return next(i for i, row in enumerate(steps, 1) if row.step_key == step.step_key), len(steps)


def summary(conversation, workflow) -> list[dict]:
	"""Every answer so far, step by step: `[{label, value}]`."""
	data = collected(conversation)
	return [
		{"label": label, "value": data[step.step_key][key]}
		for step in ordered(workflow)
		for key, label in fields(step).items()
		if data.get(step.step_key, {}).get(key)
	]


def label(step) -> str:
	return frappe.unscrub(step.step_key)


def _following(workflow, step):
	if step.next_step_key:
		return find(workflow, step.next_step_key)
	steps = ordered(workflow)
	index = next(i for i, row in enumerate(steps) if row.step_key == step.step_key)
	return steps[index + 1] if index + 1 < len(steps) else None
