"""Who may use the assistant. Checked on the server by every endpoint that reaches a model."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

DESK_ROLE = "Desk User"
REQUESTS_PER_MINUTE = 20

# Applied to every endpoint that reaches a model; counted per user and endpoint.
limit_requests = rate_limit(limit=REQUESTS_PER_MINUTE, seconds=60, user_based=True, ip_based=False)


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


def ensure_assistant_access() -> None:
	if not can_use_assistant():
		frappe.throw(_("You are not allowed to use the assistant."), frappe.PermissionError)
