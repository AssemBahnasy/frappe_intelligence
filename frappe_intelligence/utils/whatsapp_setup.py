"""Post-migrate hook — grant AI roles access to frappe_whatsapp DocTypes.

Mirrors the pattern used by frappe_crm's add_roles() utility.
Safe to call when frappe_whatsapp is not installed: returns immediately.
"""
from __future__ import annotations

import frappe


def add_whatsapp_roles() -> None:
    """Grant the 'AI Agent' role read+write on WhatsApp DocTypes.

    Called from hooks.py after_migrate. No-op if frappe_whatsapp is absent.
    Skips any permission that already exists to remain idempotent.
    """
    if "frappe_whatsapp" not in frappe.get_installed_apps():
        return

    try:
        from frappe.permissions import add_permission, update_permission_property
    except ImportError:
        return

    role = "AI Agent"
    for doctype in ("WhatsApp Message", "WhatsApp Profiles", "WhatsApp Flow"):
        if not frappe.db.exists("DocType", doctype):
            continue
        if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
            continue
        add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", 1)
        update_permission_property(doctype, role, 0, "write", 1)
