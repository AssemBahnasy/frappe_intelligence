"""Who may use the assistant. Checked on the server by every endpoint that reaches a model."""

from inspect import signature

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

DESK_ROLE = "Desk User"
REQUESTS_PER_MINUTE = 20


def requests_limit():
	"""Frappe's rate limit, counted per user and endpoint. Frappe releases from before `user_based`
	only count per IP address, so there the limit is per address."""
	if "user_based" in signature(rate_limit).parameters:
		return rate_limit(limit=REQUESTS_PER_MINUTE, seconds=60, user_based=True, ip_based=False)
	return rate_limit(limit=REQUESTS_PER_MINUTE, seconds=60)


# Applied to every endpoint that reaches a model.
limit_requests = requests_limit()


def allowed_roles() -> list[str]:
	"""AI Settings → Allowed Roles; empty means every desk user."""
	return [row.role for row in frappe.get_cached_doc("AI Settings").widget_roles]


def can_use_assistant(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Guest":
		return False
	roles = set(frappe.get_roles(user))
	if DESK_ROLE not in roles:
		return False
	allowed = allowed_roles()
	return not allowed or bool(roles.intersection(allowed))


def agent_mode_allowed() -> bool:
	return bool(frappe.get_cached_doc("AI Settings").allow_agent_mode)


def field_writer_allowed() -> bool:
	return bool(frappe.get_cached_doc("AI Settings").allow_field_writer)


def ensure_assistant_access() -> None:
	if not can_use_assistant():
		frappe.throw(_("You are not allowed to use the assistant."), frappe.PermissionError)
