"""What the assistant panel shows of workflows: the ones a user can start, and the bar above a running
one (approved board 3b): step, progress, answers so far, what is still needed, quick replies."""

from __future__ import annotations

from collections import Counter

import frappe

from frappe_intelligence.utils.fields import writable_fieldname
from frappe_intelligence.workflows import steps

MAX_CHOICES = 6


def startable() -> list[dict]:
	"""Active workflows with steps, allowed on the desk: `[{name, title, steps}]`."""
	workflows = frappe.get_all(
		"AI Workflow",
		filters={"is_active": 1, "allow_desk": 1},
		fields=["name", "title"],
		order_by="title asc",
	)
	parents = frappe.get_all(
		"AI Workflow Step",
		filters={"parenttype": "AI Workflow", "parent": ("in", [w.name for w in workflows] or [""])},
		pluck="parent",
	)
	counts = Counter(parents)
	return [{"name": w.name, "title": w.title, "steps": counts[w.name]} for w in workflows if counts[w.name]]


def progress(conversation) -> dict | None:
	if not conversation.workflow or not frappe.db.exists("AI Workflow", conversation.workflow):
		return None
	workflow = frappe.get_doc("AI Workflow", conversation.workflow)
	step = steps.current(conversation, workflow) if conversation.status != "Abandoned" else None
	labels = steps.fields(step) if step else {}
	missing = steps.missing(conversation, step) if step else []
	number, total = steps.position(workflow, step) if step else (None, len(workflow.steps or []))
	return {
		"title": workflow.title,
		"status": conversation.status,
		"step": number,
		"steps": total,
		"step_label": steps.label(step) if step else None,
		"answers": steps.summary(conversation, workflow),
		"missing": [labels[key] for key in missing],
		"choices": choices(step, missing[0]) if missing else [],
	}


def choices(step, key: str) -> list[str]:
	"""Quick replies for a field with few possible values: a short Select, or a Link to a short list."""
	if not step.target_doctype:
		return []
	meta = frappe.get_meta(step.target_doctype)
	df = meta.get_field(writable_fieldname(meta, key) or "")
	if not df:
		return []
	if df.fieldtype == "Select":
		options = [option for option in (df.options or "").split("\n") if option.strip()]
	elif df.fieldtype == "Link" and frappe.has_permission(df.options, "read"):
		options = frappe.get_list(
			df.options, filters=_selectable(df.options), pluck="name", limit=MAX_CHOICES + 1
		)
	else:
		return []
	return options if len(options) <= MAX_CHOICES else []


def _selectable(doctype: str) -> dict:
	"""Records a link can point to: not a tree's groups ("All Customer Groups"), not disabled ones."""
	meta = frappe.get_meta(doctype)
	return {
		**({"is_group": 0} if meta.is_tree else {}),
		**({"disabled": 0} if meta.has_field("disabled") else {}),
	}
