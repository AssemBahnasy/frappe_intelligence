# Using it from another app

What another Frappe app can add once frappe_intelligence is installed ([install.md](install.md)). Seed these from the app's `after_install`; keep the records in the app's `data/` folder as JSON ([../guidelines/code.md](../guidelines/code.md#python)).

| What | Gives | Doc |
|---|---|---|
| Document templates | The assistant reads the app's documents into fields the user checks | [../documents/templates.md](../documents/templates.md) |
| Document requirements | Which document types a record needs, for `api.documents.get_required_documents` | [../documents/pipeline.md](../documents/pipeline.md) |
| Post-processors | A Python callback that fills a record after a document is read | [../workflows/post-processors.md](../workflows/post-processors.md) |
| Knowledge packs | Facts the assistant and workflows search | [../workflows/knowledge-packs.md](../workflows/knowledge-packs.md) |
| Workflows | Guided data collection for the app's records | [../workflows/building.md](../workflows/building.md) |

## Seeding templates

```python
# your_app/install.py
import os

from frappe_intelligence.utils.seed_manager import seed_template_bundle


def after_install():
	seed_template_bundle(os.path.join(os.path.dirname(__file__), "data", "templates.json"))
```

`seed_template_bundle` skips templates that already exist, so changes made in the desk are kept. The bundle format: [../documents/templates.md](../documents/templates.md#bundle-format).

## Seeding requirements

```python
frappe.get_doc({
	"doctype": "AI Document Requirement",
	"target_doctype": "Purchase Invoice",
	"document_type_key": "supplier_invoice",
	"label": "Supplier Invoice",
	"is_active": 1,
}).insert(ignore_permissions=True)
```

Check that the row does not exist first; the app's own `utils/requirement_seeder.py` shows the pattern.

## Calling it from code

The endpoints are listed in [../api/](../api/README.md). From Python, the feature modules can be called directly; every model call goes through `providers.get_provider()`.
