"""Who may use the assistant, and Agent mode. Checked on the server by every endpoint that reaches a
model; see docs/setup/permissions.md."""

from inspect import signature

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

DESK_ROLE = "Desk User"
# The assistant's roles, named in AI Conversation's permissions so Frappe creates them on migrate.
USER_ROLE = "Intelligence User"  # the assistant in Ask mode
AGENT_ROLE = "Intelligence Agent"  # Agent mode as well
REQUESTS_PER_MINUTE = 20


def requests_limit():
	"""Frappe's rate limit, counted per user and endpoint. Frappe releases from before `user_based`
	only count per IP address, so there the limit is per address."""
	if "user_based" in signature(rate_limit).parameters:
		return rate_limit(limit=REQUESTS_PER_MINUTE, seconds=60, user_based=True, ip_based=False)
	return rate_limit(limit=REQUESTS_PER_MINUTE, seconds=60)


# Applied to every endpoint that reaches a model.
limit_requests = requests_limit()


def user_roles(user: str | None = None) -> list[str]:
	"""The user's roles. Administrator follows the roles ticked on its own User form: Frappe gives it
	every role (frappe.permissions.get_roles), which would make unticking them mean nothing here."""
	user = user or frappe.session.user
	if user != "Administrator":
		return frappe.get_roles(user)
	ticked = [row.role for row in frappe.get_cached_doc("User", user).roles]
	return [*ticked, DESK_ROLE]


def can_use_assistant(user: str | None = None) -> bool:
	"""A desk user with either role."""
	user = user or frappe.session.user
	if user == "Guest":
		return False
	roles = user_roles(user)
	return DESK_ROLE in roles and (USER_ROLE in roles or AGENT_ROLE in roles)


def agent_mode_refusal(user: str | None = None) -> str | None:
	"""Why Agent mode is closed to the user, or None when it is open: it must be on in AI Settings,
	and the user must have the Intelligence Agent role."""
	if not frappe.get_cached_doc("AI Settings").allow_agent_mode:
		return _("Agent mode is turned off in AI Settings.")
	if AGENT_ROLE not in user_roles(user):
		return _("You have not been given Agent mode. Ask your administrator.")
	return None


def field_writer_allowed() -> bool:
	return bool(frappe.get_cached_doc("AI Settings").allow_field_writer)


def ensure_assistant_access() -> None:
	if not can_use_assistant():
		frappe.throw(_("You are not allowed to use the assistant."), frappe.PermissionError)
