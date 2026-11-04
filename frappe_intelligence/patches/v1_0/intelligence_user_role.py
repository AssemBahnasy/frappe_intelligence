"""Who may use the assistant moved from AI Settings → Allowed Roles to the Intelligence User role.
Everyone the old rule let in gets the role, so nothing changes for them; Allowed Roles goes, with its
child DocType AI Widget Role (deleting a DocType keeps its table, so the table is dropped too)."""

import frappe

from frappe_intelligence.utils.access import USER_ROLE

OLD_TABLE = "AI Widget Role"


def execute():
	if frappe.db.table_exists(OLD_TABLE):
		allowed = frappe.db.sql(f"SELECT role FROM `tab{OLD_TABLE}` WHERE parent = 'AI Settings'", pluck=True)
		for user in users_with_access(allowed):
			frappe.get_doc("User", user).add_roles(USER_ROLE)
	frappe.delete_doc("DocType", OLD_TABLE, ignore_missing=True, force=True)
	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{OLD_TABLE}`")


def users_with_access(allowed_roles: list[str]) -> list[str]:
	"""Enabled desk users the old rule let in: any with one of the allowed roles, or every one of
	them when no role was set. Administrator always had every role, so it is always one of them; it
	now follows its ticked roles (utils/access.user_roles), so it gets the role too."""
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["!=", "Guest"]},
		pluck="name",
	)
	if not allowed_roles or not users:
		return users
	with_role = set(
		frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "parent": ["in", users], "role": ["in", allowed_roles]},
			pluck="parent",
		)
	)
	return [user for user in users if user == "Administrator" or user in with_role]
