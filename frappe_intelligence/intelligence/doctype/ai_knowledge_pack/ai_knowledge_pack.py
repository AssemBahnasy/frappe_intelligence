import json

import frappe
from frappe.model.document import Document


class AIKnowledgePack(Document):

    def after_insert(self):
        if self.json_file:
            self._import_from_file()

    def _import_from_file(self):
        """Parse the attached JSON bundle and upsert AI Document Templates and knowledge entries."""
        from frappe_intelligence.utils.seed_manager import import_pack_data

        file_doc = frappe.get_doc("File", {"file_url": self.json_file})
        raw = file_doc.get_content()
        data = json.loads(raw)

        imported, skipped = import_pack_data(data)

        # Import knowledge entries if the bundle includes them
        entries = data.get("knowledge_entries", [])
        entry_count = 0
        for entry in entries:
            topic = (entry.get("topic") or "").strip()
            content = (entry.get("content") or "").strip()
            if topic and content:
                self.append("knowledge_entries", {"topic": topic, "content": content})
                entry_count += 1

        if entry_count:
            self.save(ignore_permissions=True)

        frappe.msgprint(
            frappe._(
                "Imported {0} template(s), skipped {1} (already exist). "
                "Added {2} knowledge entry/entries."
            ).format(imported, skipped, entry_count)
        )
