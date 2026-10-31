"""A conversation as the panel shows it: one entry per question, with its files, steps, changes,
document reviews and answer. A guided workflow's opening question is an entry without a question."""

from __future__ import annotations

import frappe

from frappe_intelligence.agent.loop import STOPPED_RESULT
from frappe_intelligence.agent.tools import needs_approval, registry, step_label
from frappe_intelligence.intelligence.doctype.ai_conversation.ai_conversation import STOPPED_NOTICE


def turns(conversation) -> list[dict]:
	result: list[dict] = []
	steps: dict[str, dict] = {}
	for row in conversation.messages:
		if row.role == "user":
			steps = {}
			result.append(_turn(row))
		elif not result and row.role == "assistant":
			result.append(_turn(row, asked=False))
			_add_reply(row, steps, result[-1])
		elif not result:
			continue
		elif row.role == "tool" and row.approval:
			# A document reading is a step too; a change is shown only as its card.
			_finish_step(steps.get(row.tool_call_id), row, result[-1])
			result[-1]["proposals"].append(_proposal(row))
		elif row.role == "tool":
			_finish_step(steps.get(row.tool_call_id), row, result[-1])
		elif row.role == "system" and row.content == STOPPED_NOTICE:
			result[-1]["stopped"] = True
		elif row.role == "assistant" and row.is_error:
			result[-1]["error"] = row.content
		elif row.role == "assistant":
			_add_reply(row, steps, result[-1])
	return result


def _turn(row, asked: bool = True) -> dict:
	return {
		"id": row.name,
		"question": row.content if asked else "",
		"attachments": frappe.parse_json(row.attachments) if asked and row.attachments else [],
		"created": row.creation,
		"steps": [],
		"proposals": [],
		"actions": [],
		"answer": "",
		"report": "",
	}


def _add_reply(row, steps: dict, turn: dict) -> None:
	for call in frappe.parse_json(row.tool_calls or "[]"):
		if needs_approval(call["name"]):
			continue  # shown as a change card instead
		step = {"label": step_label(call["name"], call.get("arguments") or {}), "status": "running"}
		steps[call["id"]] = step
		turn["steps"].append(step)
	if row.content:
		# Text written after a change was proposed reports on it, so it shows under the change.
		part = "report" if turn["proposals"] else "answer"
		turn[part] = "\n\n".join(filter(None, [turn[part], row.content]))
		turn.update(answer_id=row.name, feedback=row.feedback or None, off_topic=bool(row.off_topic))


def _proposal(row) -> dict:
	"""status: pending, rejected, done (approved and made, or values confirmed) or failed (approved,
	but it did not work)."""
	status = row.approval.lower()
	if row.approval == "Approved":
		status = "failed" if row.is_error else ("done" if row.content else "approved")
	return {
		"call_id": row.tool_call_id,
		"status": status,
		"preview": frappe.parse_json(row.preview) if row.preview else {},
		"error": row.content if row.is_error else None,
		"result": _created_name(row) if status == "done" else None,
	}


def _created_name(row) -> str | None:
	result = frappe.parse_json(row.content)
	return result.get("created") if isinstance(result, dict) else None


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
