"""AI Workflow session management and step machine.

This module is the single source of truth for workflow state. It owns:
  - Session lookup / creation (get_or_create_session)
  - Current step resolution (get_current_step)
  - Partial field collection (collect_step_data)
  - Step advancement (advance_step)
  - Prompt building for the LLM (build_step_prompt)
  - Turn append (append_turn)

All session state is persisted to the AI Agent Session DocType so that it
survives server restarts, channel switches (desk → WhatsApp), and the 2-hour
Redis TTL that the old fi_chat:{sid} approach had.
"""

import json
from datetime import datetime

import frappe
from frappe.utils import now_datetime


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def get_or_create_session(channel: str, channel_id: str, workflow_key: str | None = None):
    """Return the active AI Agent Session for this channel + channel_id.

    Creates a new session if none exists or the existing one is completed/abandoned.

    :param channel: "desk" | "portal" | "whatsapp"
    :param channel_id: session SID, portal username, or formatted phone number
    :param workflow_key: AI Workflow.workflow_key to associate. If None, returned
                         session may have no workflow (free-chat mode).
    """
    existing = frappe.db.get_value(
        "AI Agent Session",
        {"channel": channel, "channel_id": channel_id, "status": "active"},
        "name",
        order_by="modified desc",
    )

    if existing:
        session = frappe.get_doc("AI Agent Session", existing)
        # If caller specifies a workflow and session has none, bind it now.
        if workflow_key and not session.workflow:
            _bind_workflow(session, workflow_key)
        return session

    session = frappe.new_doc("AI Agent Session")
    session.channel = channel
    session.channel_id = channel_id
    session.status = "active"
    session.collected_data = json.dumps({})

    if workflow_key:
        _bind_workflow(session, workflow_key, save=False)

    session.insert(ignore_permissions=True)
    return session


def _bind_workflow(session, workflow_key: str, save: bool = True):
    """Attach an AI Workflow to a session and set the first step as current."""
    if not frappe.db.exists("AI Workflow", workflow_key):
        frappe.log_error(f"AI Workflow '{workflow_key}' not found.", "workflow.py")
        return

    workflow = frappe.get_doc("AI Workflow", workflow_key)
    session.workflow = workflow_key

    first_step = _first_step(workflow)
    if first_step:
        session.current_step = first_step.step_key

    if save:
        session.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Step resolution
# ---------------------------------------------------------------------------

def get_current_step(session):
    """Return the AI Workflow Step child row for session.current_step, or None."""
    if not session.workflow or not session.current_step:
        return None

    workflow = frappe.get_doc("AI Workflow", session.workflow)
    for step in workflow.steps or []:
        if step.step_key == session.current_step:
            return step

    # Step key no longer exists in the live workflow — it was edited mid-session.
    frappe.log_error(
        f"Session {session.name}: step '{session.current_step}' not found in "
        f"workflow '{session.workflow}' — session abandoned (workflow was edited).",
        "workflow.py",
    )
    session.status = "abandoned"
    session.save(ignore_permissions=True)
    return None


def get_workflow(session):
    """Return the AI Workflow document linked to this session, or None."""
    if not session.workflow:
        return None
    return frappe.get_doc("AI Workflow", session.workflow)


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect_step_data(session, step, extracted: dict) -> tuple[dict, bool]:
    """Merge extracted data into session.collected_data for the current step.

    :param session: AI Agent Session document.
    :param step: AI Workflow Step child row.
    :param extracted: Dict of {fieldname: value} parsed from user input.
    :returns: (all_collected_so_far, step_is_complete)
    """
    collected = json.loads(session.collected_data or "{}")
    step_data = collected.get(step.step_key, {})
    step_data.update({k: v for k, v in extracted.items() if v is not None})
    collected[step.step_key] = step_data

    session.collected_data = json.dumps(collected)
    session.save(ignore_permissions=True)

    required = _required_field_keys(step)
    complete = all(step_data.get(f) for f in required)
    return collected, complete


def get_collected_for_step(session, step_key: str) -> dict:
    """Return the collected field values for a specific step."""
    collected = json.loads(session.collected_data or "{}")
    return collected.get(step_key, {})


# ---------------------------------------------------------------------------
# Step advancement
# ---------------------------------------------------------------------------

def advance_step(session):
    """Move session to the next step. Mark completed if no next step.

    :returns: The new AI Workflow Step child row, or None if workflow is done.
    """
    if not session.workflow or not session.current_step:
        _mark_completed(session)
        return None

    workflow = frappe.get_doc("AI Workflow", session.workflow)
    current = None
    for step in workflow.steps or []:
        if step.step_key == session.current_step:
            current = step
            break

    if not current:
        _mark_completed(session)
        return None

    next_key = current.next_step_key
    if next_key:
        # Find the explicit next step by key
        for step in workflow.steps or []:
            if step.step_key == next_key:
                session.current_step = next_key
                session.save(ignore_permissions=True)
                return step
        # next_step_key set but not found — treat as complete
        _mark_completed(session)
        return None
    else:
        # No explicit next → find by order
        sorted_steps = sorted(workflow.steps or [], key=lambda s: s.step_order)
        found_current = False
        for step in sorted_steps:
            if found_current:
                session.current_step = step.step_key
                session.save(ignore_permissions=True)
                return step
            if step.step_key == session.current_step:
                found_current = True

        _mark_completed(session)
        return None


def _mark_completed(session):
    session.status = "completed"
    session.current_step = ""
    session.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_step_prompt(step, collected_so_far: dict, workflow_doc=None) -> str:
    """Build the LLM system prompt fragment for the current workflow step.

    Injects the step's mandate, what has been collected so far, and what
    still needs to be gathered. The caller merges this with the global
    AI Settings system prompt.
    """
    lines = []

    if workflow_doc and workflow_doc.scope_description:
        lines.append(f"## Your mandate\n{workflow_doc.scope_description}")

    lines.append(f"\n## Current task: {step.prompt_to_user or step.step_key}")

    required = _required_field_keys(step)
    labels = _required_field_labels(step)

    already = {f: collected_so_far.get(f) for f in required if collected_so_far.get(f)}
    missing = [f for f in required if not collected_so_far.get(f)]

    if already:
        lines.append("\n### Already collected")
        for f, v in already.items():
            lines.append(f"- {labels.get(f, f)}: {v}")

    if missing:
        lines.append("\n### Still needed from the user")
        for f in missing:
            lines.append(f"- {labels.get(f, f)}")
        lines.append(
            "\nAsk the user for the missing information above. "
            "Collect only what is listed. Do not ask for anything else."
        )
    else:
        lines.append(
            "\nAll required information has been collected. "
            "Confirm the details with the user and proceed."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Turn management
# ---------------------------------------------------------------------------

def append_turn(session, role: str, content: str):
    """Append a conversation turn to the session's Turns child table."""
    session.append("turns", {
        "role": role,
        "content": content,
        "timestamp": now_datetime(),
    })
    session.save(ignore_permissions=True)


def get_turn_history(session, max_turns: int = 20) -> list[dict]:
    """Return the last N turns as a list of {role, content} dicts for LLM context."""
    turns = session.turns or []
    recent = turns[-max_turns:] if len(turns) > max_turns else turns
    return [{"role": t.role, "content": t.content} for t in recent]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _first_step(workflow):
    """Return the step with the lowest step_order."""
    steps = sorted(workflow.steps or [], key=lambda s: s.step_order)
    return steps[0] if steps else None


def _required_field_keys(step) -> list[str]:
    """Parse required_fields JSON and return the list of field keys."""
    if not step.required_fields:
        return []
    try:
        data = json.loads(step.required_fields)
        return list(data.keys())
    except (json.JSONDecodeError, TypeError):
        return []


def _required_field_labels(step) -> dict[str, str]:
    """Parse required_fields JSON and return {key: label} mapping."""
    if not step.required_fields:
        return {}
    try:
        return json.loads(step.required_fields)
    except (json.JSONDecodeError, TypeError):
        return {}
