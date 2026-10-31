"""Python callables administrators name in settings (post-processors, workflow completion checks)."""

from __future__ import annotations

import frappe


def is_app_method(method: str | None) -> bool:
	"""Only a dotted path inside an installed Frappe app, so a setting cannot name `os.system` or the like."""
	if not method or not isinstance(method, str):
		return False
	parts = method.split(".")
	if len(parts) < 2 or any(part == "" for part in parts):
		return False
	return parts[0] in frappe.get_installed_apps()
