"""
api/portal.py
-------------
Whitelisted endpoints for portal-channel callers (React / Vue portals, Frappe
web portal). Kept apart from the desk endpoints: different auth model, different
caller audience.

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

Portal always runs in workflow mode, without desk tools — there is no
``frappe.set_route()`` in a React or Vue portal.
"""

from __future__ import annotations

import frappe

from frappe_intelligence.utils.access import limit_requests
from frappe_intelligence.utils.file_utils import validate_file_access

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
	if not frappe.db.exists(
		"Portal User",
		{
			"user": frappe.session.user,
			"parent": customer,
			"parenttype": "Customer",
		},
	):
		frappe.throw(
			frappe._("Access denied."),
			frappe.PermissionError,
		)


# ---------------------------------------------------------------------------
# Whitelisted endpoints
# ---------------------------------------------------------------------------


@frappe.whitelist()
@limit_requests
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

	from frappe_intelligence.engine.chat import workflow_reply

	return workflow_reply(text, "Portal", frappe.session.user, workflow_key)


@frappe.whitelist()
@limit_requests
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
	Return the current workflow conversation state for this portal user + workflow.

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

	session = _wf.get_or_create_session("Portal", frappe.session.user, workflow_key)
	step = _wf.get_current_step(session)

	return {
		"status": session.status,
		"current_step": session.current_step,
		"step_prompt": step.prompt_to_user if step else None,
		"collected_data": frappe.parse_json(session.collected_data or "{}"),
	}
