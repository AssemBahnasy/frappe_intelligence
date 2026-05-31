"""
api_portal.py
-------------
Whitelisted endpoints for portal-channel callers (React / Vue portals, Frappe
web portal).  Do NOT merge into api.py — different auth model, different caller
audience.

Auth model
~~~~~~~~~~
Every endpoint calls ``_assert_portal_user(customer)`` first:
  • Guest → AuthenticationError
  • Logged-in user not in the Customer's Portal User child table → PermissionError

Channel identity
~~~~~~~~~~~~~~~~
``channel_id = frappe.session.user`` — stable email, unique per person, survives
session expiry and multiple devices.  NOT ``session.sid`` (expires in 2 h) and
NOT ``customer`` (would merge all users of the same company into one session).

Portal always runs in workflow mode.  FRAPPE_TOOLS are never passed — there is
no ``frappe.set_route()`` in a React or Vue portal.
"""
from __future__ import annotations

import frappe

from frappe_intelligence.utils.file_utils import validate_file_access

# Per-customer rate limit for portal callers.
# Portal users are Website Users — the desk rate limit key fi_rl:{session.user}
# must NOT be used here (Website Users share the "Guest" context in some paths).
_PORTAL_RATE_LIMIT_MAX = 20
_PORTAL_RATE_LIMIT_WINDOW = 60  # seconds


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _assert_portal_user(customer: str) -> None:
    """Raise an appropriate exception if the caller is not a portal user of *customer*."""
    if frappe.session.user == "Guest":
        frappe.throw(
            frappe._("Authentication required."),
            frappe.AuthenticationError,
        )
    if not frappe.db.exists("Portal User", {
        "user": frappe.session.user,
        "parent": customer,
        "parenttype": "Customer",
    }):
        frappe.throw(
            frappe._("Access denied."),
            frappe.PermissionError,
        )


def _enforce_portal_rate_limit(customer: str) -> None:
    """Raise RateLimitExceededError when this customer has hit the per-window cap."""
    key = f"fi_rl_portal:{customer}"
    count = frappe.cache().get_value(key) or 0
    if count >= _PORTAL_RATE_LIMIT_MAX:
        frappe.throw(
            frappe._("Too many requests. Please wait a moment before trying again."),
            frappe.RateLimitExceededError,
        )
    frappe.cache().set_value(key, count + 1, expires_in_sec=_PORTAL_RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Whitelisted endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def portal_chat(
    text: str,
    customer: str,
    workflow_key: str,
    context_hint: str | None = None,
) -> dict:
    """
    Send a text message on the portal channel and return the AI reply.

    Parameters
    ----------
    text:
        The user's message.
    customer:
        ERPNext Customer name — used for auth and rate limiting.
    workflow_key:
        ``AI Workflow.workflow_key`` that governs this session.
    context_hint:
        Optional free-text context passed from the portal UI (e.g. current page name).
        Currently forwarded to the engine for future use; not yet consumed.

    Returns
    -------
    ``{"reply": str, "action": str | None, "action_data": dict | None}``
    """
    _assert_portal_user(customer)
    _enforce_portal_rate_limit(customer)

    from frappe_intelligence.engine.chat import classify_text_intent
    return classify_text_intent(
        text=text,
        doctype=None,
        docname=None,
        channel="portal",
        channel_id=frappe.session.user,
        workflow_key=workflow_key,
    )


@frappe.whitelist()
def portal_upload_document(
    file_url: str,
    customer: str,
    target_doctype: str | None = None,
) -> dict:
    """
    Enqueue document processing for a portal upload and return immediately.

    Uses the same long-queue async pipeline as ``api.process_document``.
    The result is delivered via the ``ai_processing_complete`` realtime event
    (``AIPortalClient.onDone`` callback).

    Parameters
    ----------
    file_url:
        Frappe file URL — ``/files/`` or ``/private/files/`` only.
    customer:
        ERPNext Customer name — used for auth only.
    target_doctype:
        Optional ``document_type_key`` of the expected AI Document Template.
        Pass ``None`` for automatic classification.

    Returns
    -------
    ``{"status": "queued", "log_name": str}``
    """
    _assert_portal_user(customer)
    validate_file_access(file_url)

    from frappe_intelligence.engine.orchestrator import AIEngine
    log = AIEngine()._create_log(file_url)

    frappe.enqueue(
        "frappe_intelligence.engine.orchestrator.process_document_background",
        queue="long",
        timeout=600,
        log_name=log.name,
        file_url=file_url,
        target_doctype=target_doctype,
        session_user=frappe.session.user,
    )

    return {"status": "queued", "log_name": log.name}


@frappe.whitelist()
def portal_get_session_state(
    customer: str,
    workflow_key: str,
) -> dict:
    """
    Return the current AI Agent Session state for this portal user + workflow.

    Creates a session if none exists yet (idempotent).

    Parameters
    ----------
    customer:
        ERPNext Customer name — used for auth only.
    workflow_key:
        ``AI Workflow.workflow_key`` to look up or create a session for.

    Returns
    -------
    ``{
        "status": str,
        "current_step": str | None,
        "step_prompt": str | None,
        "collected_data": dict,
    }``
    """
    _assert_portal_user(customer)

    from frappe_intelligence.engine import workflow as _wf
    session = _wf.get_or_create_session("portal", frappe.session.user, workflow_key)
    step = _wf.get_current_step(session)

    return {
        "status": session.status,
        "current_step": session.current_step,
        "step_prompt": step.prompt_to_user if step else None,
        "collected_data": frappe.parse_json(session.collected_data or "{}"),
    }
