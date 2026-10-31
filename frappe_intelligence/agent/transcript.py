"""A conversation as the panel shows it: one entry per question, with its steps and answer."""

from __future__ import annotations

import frappe

from frappe_intelligence.agent.loop import STOPPED_RESULT
from frappe_intelligence.agent.tools import registry, step_label
from frappe_intelligence.intelligence.doctype.ai_conversation.ai_conversation import STOPPED_NOTICE


def turns(conversation) -> list[dict]:
	result: list[dict] = []
	steps: dict[str, dict] = {}
	for row in conversation.messages:
		if row.role == "user":
			steps = {}
			result.append(
				{"id": row.name, "question": row.content, "created": row.creation, "steps": [], "actions": []}
			)
		elif not result:
			continue
		elif row.role == "assistant" and row.tool_calls:
			for call in frappe.parse_json(row.tool_calls):
				step = {"label": step_label(call["name"], call.get("arguments") or {}), "status": "running"}
				steps[call["id"]] = step
				result[-1]["steps"].append(step)
		elif row.role == "tool":
			_finish_step(steps.get(row.tool_call_id), row, result[-1])
		elif row.role == "system" and row.content == STOPPED_NOTICE:
			result[-1]["stopped"] = True
		elif row.role == "assistant" and row.is_error:
			result[-1]["error"] = row.content
		elif row.role == "assistant":
			result[-1].update(answer=row.content, answer_id=row.name, feedback=row.feedback or None)
	return result


def _finish_step(step: dict | None, row, turn: dict) -> None:
	if step is None:
		return
	if row.content == STOPPED_RESULT:
		step["status"] = "stopped"
	elif row.is_error:
		step["status"] = "failed"
	else:
		step["status"] = "done"
		tool = registry().get(row.tool_name)
		if tool and tool.browser_action:
			turn["actions"].append(frappe.parse_json(row.content)["action"])
