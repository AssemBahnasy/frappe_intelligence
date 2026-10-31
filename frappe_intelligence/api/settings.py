"""What the AI Settings form asks the server: connection test, WhatsApp availability."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def test_connection() -> dict:
	"""
	Verify that the currently configured AI provider is reachable.

	Requires System Manager.

	Returns
	-------
	``{"ok": True}`` on success, ``{"ok": False, "error": str}`` on failure.
	"""
	frappe.only_for("System Manager")
	from frappe_intelligence.providers import ProviderError, get_provider

	try:
		get_provider().test_connection()
	except ProviderError as exc:
		return {"ok": False, "error": str(exc)}
	return {"ok": True}


@frappe.whitelist()
def is_whatsapp_installed() -> bool:
	"""True when frappe_whatsapp is installed on this site.

	Checks for the WhatsApp Settings DocType — it is created by
	frappe_whatsapp on install and removed on uninstall.
	"""
	return bool(frappe.db.exists("DocType", "WhatsApp Settings"))


@frappe.whitelist()
def is_whatsapp_enabled() -> bool:
	"""True when frappe_whatsapp is installed, a default incoming account
	exists, that account's status is 'Active', AND AI Settings has the
	enable_ai_on_whatsapp switch turned on.

	Called by:
	  - AI Settings form JS → show/hide WhatsApp config section
	  - Vue Workflow Builder → show/hide 'WhatsApp Flow' step fields
	  - whatsapp_handler.py → guard before processing any incoming message
	"""
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	try:
		enabled = frappe.db.get_single_value("AI Settings", "enable_ai_on_whatsapp")
		if not enabled:
			return False
		default_account = frappe.db.get_single_value("WhatsApp Settings", "default_incoming_account")
		if not default_account:
			return False
		status = frappe.db.get_value("WhatsApp Account", default_account, "status")
		return status == "Active"
	except Exception:
		return False
