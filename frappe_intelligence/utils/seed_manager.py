"""
seed_manager.py
---------------
Utility for seeding AI Document Templates from a JSON bundle file.

Each Frappe application that integrates frappe_intelligence is responsible
for defining its own document templates and seeding them at install time.
frappe_intelligence itself ships with no pre-built templates — it is a
domain-neutral infrastructure layer.

Expected JSON schema for a bundle file::

    {
        "templates": [
            {
                "document_type_key": "my_doc",
                "document_name": "My Document",
                "model_preference": "Both",
                "detection_keywords": "keyword one, keyword two",
                "extraction_rules": [
                    {
                        "field_key": "field_one",
                        "label": "Field One",
                        "extraction_strategy": "Regex",
                        "regex_pattern": "pattern",
                        "llm_hint": ""
                    }
                ]
            }
        ]
    }

The top-level object may also be a bare JSON array of template objects.
"""
from __future__ import annotations

import json
from pathlib import Path

import frappe


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upsert_template(data: dict) -> bool:
    """
    Create an AI Document Template from *data*.

    Returns True if a new record was created, False if it already existed.
    Existing records are never overwritten so user customisations are preserved.
    """
    key = data.get("document_type_key", "").strip().lower()
    if not key:
        frappe.log_error(
            "Seed entry missing 'document_type_key' – skipped.", "SeedManager")
        return False

    if frappe.db.exists("AI Document Template", key):
        return False

    doc = frappe.new_doc("AI Document Template")
    doc.document_type_key = key
    doc.document_name = data.get("document_name", key)
    doc.model_preference = data.get("model_preference", "Heuristic")
    doc.detection_keywords = data.get("detection_keywords", "")
    doc.is_active = 1

    for rule in data.get("extraction_rules", []):
        doc.append("extraction_rules", {
            "field_key": rule.get("field_key", ""),
            "label": rule.get("label", ""),
            "extraction_strategy": rule.get("extraction_strategy", "Regex"),
            "regex_pattern": rule.get("regex_pattern", ""),
            "llm_hint": rule.get("llm_hint", ""),
        })

    doc.insert(ignore_permissions=True)
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def import_pack_data(data: dict | list) -> tuple[int, int]:
    """
    Import templates from a parsed bundle dict or list.

    Called by AIKnowledgePack.after_insert() when a JSON file is uploaded.

    Returns ``(imported_count, skipped_count)``.
    """
    imported, skipped = 0, 0
    templates = data if isinstance(data, list) else data.get("templates", [data])

    for entry in templates:
        if _upsert_template(entry):
            imported += 1
        else:
            skipped += 1

    return imported, skipped


def seed_template_bundle(bundle_path: "Path | str") -> tuple[int, int]:
    """
    Seed AI Document Templates from a JSON bundle file.

    Call this from your application's ``after_install`` hook, passing the
    path to a bundle JSON file that you ship inside your own app.

    Parameters
    ----------
    bundle_path:
        Absolute path to a JSON bundle file inside your application.

    Returns
    -------
    ``(imported_count, skipped_count)``

    The seeder never overwrites existing records, so it is safe to call on
    every install or migrate.

    Example — inside your app's ``install.py``::

        from pathlib import Path
        from frappe_intelligence.utils.seed_manager import seed_template_bundle

        def after_install():
            bundle = Path(__file__).parent / "data" / "ai_templates.json"
            imported, skipped = seed_template_bundle(bundle)
    """
    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        frappe.log_error(
            f"Bundle file not found: {bundle_path}", "SeedManager"
        )
        return 0, 0

    try:
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        frappe.log_error(
            f"Cannot parse bundle {bundle_path.name}: {exc}", "SeedManager"
        )
        return 0, 0

    return import_pack_data(data)
