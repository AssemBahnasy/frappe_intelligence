"""
requirement_seeder.py
---------------------
Seeds default AI Document Requirement records for well-known DocTypes.

Called automatically from after_install.  Admins can add/remove/edit
requirements at any time via the Frappe desk without running code.
"""
import frappe

# -----------------------------------------------------------------------
# Default requirements: { target_doctype: [(document_type_key, label)] }
# Add more entries here as new integrating apps and document types are built.
# -----------------------------------------------------------------------
_DEFAULT_REQUIREMENTS: dict[str, list[tuple[str, str]]] = {}


def seed_requirements() -> tuple[int, int]:
    """
    Insert default AI Document Requirement records if they don't exist yet.

    Returns
    -------
    (inserted, skipped)
    """
    inserted = 0
    skipped = 0

    for target_doctype, reqs in _DEFAULT_REQUIREMENTS.items():
        for doc_key, label in reqs:
            exists = frappe.db.exists(
                "AI Document Requirement",
                {"target_doctype": target_doctype, "document_type_key": doc_key},
            )
            if exists:
                skipped += 1
                continue

            doc = frappe.new_doc("AI Document Requirement")
            doc.target_doctype = target_doctype
            doc.document_type_key = doc_key
            doc.label = label
            doc.is_active = 1
            doc.insert(ignore_permissions=True)
            inserted += 1

    return inserted, skipped
