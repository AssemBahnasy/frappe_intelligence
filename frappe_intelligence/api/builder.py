"""Workflow Builder page endpoints (System Manager)."""

from __future__ import annotations

import json as _json

import frappe


@frappe.whitelist()
def list_workflows() -> list[dict]:
	"""Return active AI Workflow records for the Ask/Agent mode selector dropdown.

	Returns
	-------
	``[{"workflow_key": str, "title": str}, ...]``
	"""
	return frappe.get_all(
		"AI Workflow",
		filters={"is_active": 1},
		fields=["workflow_key", "title"],
		order_by="title asc",
	)


@frappe.whitelist()
def get_workflow_for_builder(workflow_key: str) -> dict:
	"""
	Return the full builder payload for a given AI Workflow.

	Used by the Vue Workflow Plan Builder page to populate its state on load.
	All data is read-only — no writes are made here.

	Returns
	-------
	``{
	    "workflow":             {workflow fields},
	    "steps":                [{step fields}, ...],
	    "knowledge_packs":      [{pack}, ...],
	    "available_packs":      [{name, pack_name, description, is_active}, ...],
	    "available_wa_flows":   [{name}, ...] or [] when frappe_whatsapp absent
	}``
	"""
	frappe.only_for("System Manager")

	wf = frappe.get_doc("AI Workflow", workflow_key)

	steps = [
		{
			"step_order": s.step_order,
			"step_key": s.step_key,
			"prompt_to_user": s.prompt_to_user,
			"target_doctype": s.target_doctype,
			"whatsapp_flow": s.whatsapp_flow,
			"required_fields": s.required_fields,
			"completion_check": s.completion_check,
			"next_step_key": s.next_step_key,
		}
		for s in (wf.steps or [])
	]

	available_packs = frappe.get_all(
		"AI Knowledge Pack",
		fields=["name", "pack_name", "description", "is_active"],
		order_by="pack_name asc",
	)

	# WhatsApp Flows — only available when frappe_whatsapp is installed.
	available_wa_flows: list[dict] = []
	if frappe.db.exists("DocType", "WhatsApp Flow"):
		available_wa_flows = frappe.get_all(
			"WhatsApp Flow",
			fields=["name"],
			order_by="name asc",
		)

	knowledge_packs = [{"pack": row.pack} for row in (wf.knowledge_packs or [])]

	return {
		"workflow": {
			"workflow_key": wf.workflow_key,
			"title": wf.title,
			"is_active": wf.is_active,
			"allow_desk": wf.allow_desk,
			"allow_portal": wf.allow_portal,
			"allow_whatsapp": wf.allow_whatsapp,
			"scope_description": wf.scope_description,
			"out_of_scope_reply": wf.out_of_scope_reply,
		},
		"steps": steps,
		"knowledge_packs": knowledge_packs,
		"available_packs": available_packs,
		"available_wa_flows": available_wa_flows,
	}


@frappe.whitelist()
def save_workflow_builder(workflow_key: str, payload: dict | str) -> dict:
	"""
	Atomically upsert an AI Workflow from the Vue builder payload.

	Persists:
	  - AI Workflow header fields (title, is_active, channels, scope, out_of_scope_reply)
	  - AI Workflow Step children (full replace — order, key, prompt, doctype, fields, etc.)
	  - Knowledge Pack assignments (``knowledge_packs`` child table, full replace)

	Parameters
	----------
	workflow_key:
	    Identifies the AI Workflow to update. Must already exist.
	payload:
	    JSON with keys: ``workflow``, ``steps``, ``knowledge_packs``.

	Returns
	-------
	``{"ok": True}``
	"""
	frappe.only_for("System Manager")

	if isinstance(payload, str):
		payload = _json.loads(payload)

	wf_data: dict = payload.get("workflow", {})
	steps_data: list[dict] = payload.get("steps", [])
	packs_data: list[dict] = payload.get("knowledge_packs", [])

	# --- Update AI Workflow header + steps (atomic via frappe.get_doc + save) ---
	wf = frappe.get_doc("AI Workflow", workflow_key)

	if wf_data.get("title"):
		wf.title = wf_data["title"]
	wf.is_active = int(wf_data.get("is_active", wf.is_active))
	wf.allow_desk = int(wf_data.get("allow_desk", wf.allow_desk))
	wf.allow_portal = int(wf_data.get("allow_portal", wf.allow_portal))
	wf.allow_whatsapp = int(wf_data.get("allow_whatsapp", wf.allow_whatsapp))
	wf.scope_description = wf_data.get("scope_description", wf.scope_description)
	wf.out_of_scope_reply = wf_data.get("out_of_scope_reply", wf.out_of_scope_reply)

	# Full replace of steps child table.
	wf.steps = []
	for s in steps_data:
		wf.append(
			"steps",
			{
				"step_order": s.get("step_order", 0),
				"step_key": s.get("step_key", ""),
				"prompt_to_user": s.get("prompt_to_user", ""),
				"target_doctype": s.get("target_doctype"),
				"whatsapp_flow": s.get("whatsapp_flow"),
				"required_fields": s.get("required_fields"),
				"completion_check": s.get("completion_check"),
				"next_step_key": s.get("next_step_key"),
			},
		)

	# Full replace of knowledge_packs child table.
	wf.knowledge_packs = []
	for p in packs_data:
		if p.get("pack"):
			wf.append("knowledge_packs", {"pack": p["pack"]})

	wf.save(ignore_permissions=True)

	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def preview_step_prompt(step_data: dict | str) -> dict:
	"""
	Return the rendered LLM prompt for an unsaved step draft.

	The Vue builder calls this as the user edits a step, debounced at 500 ms.
	``step_data`` contains the same fields as an AI Workflow Step child row but
	may be partially filled (unsaved draft state).

	Parameters
	----------
	step_data:
	    Dict with step fields (step_key, prompt_to_user, required_fields, …).

	Returns
	-------
	``{"prompt": str}``
	"""
	frappe.only_for("System Manager")

	if isinstance(step_data, str):
		step_data = _json.loads(step_data)

	from types import SimpleNamespace

	from frappe_intelligence.workflows.turn import step_instructions

	step = SimpleNamespace(
		step_key=step_data.get("step_key", ""),
		prompt_to_user=step_data.get("prompt_to_user", ""),
		required_fields=step_data.get("required_fields"),
	)
	prompt = step_instructions(step, given={})
	return {"prompt": prompt}
