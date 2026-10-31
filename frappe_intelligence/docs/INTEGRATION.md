# Integration

How to add `frappe_intelligence` to another Frappe app.

## 1. Install

```bash
bench get-app frappe_intelligence
bench --site <site> install-app frappe_intelligence
bench --site <site> migrate
bench build --app frappe_intelligence
```

The assistant appears in the dock and sidebar of every Frappe Desk page after the build (open it with Ctrl+.). No template changes needed.

## 2. Configure the AI Provider

Open **AI Settings → Model tab**. Set Provider, fill in the provider fields, Save, Test Connection.

See [CONFIGURATION.md](CONFIGURATION.md) for all fields. See [DEPLOYMENT.md](DEPLOYMENT.md) for Ollama vs Claude trade-offs.

## 3. Define Document Templates

The app ships with zero templates — define yours.

**Via desk:** AI Document Template → New.

**Via bundle file** (recommended for apps):

```python
# your_app/install.py
from frappe_intelligence.utils.seed_manager import seed_template_bundle
import os

def after_install():
    seed_template_bundle(
        os.path.join(os.path.dirname(__file__), "data", "templates.json")
    )
```

See [DOCUMENT_PIPELINE.md](DOCUMENT_PIPELINE.md) for the bundle format.

## 4. Register Document Requirements (optional)

Enables the proactive bubble and Smart Checklist on your DocType forms.

```python
# your_app/install.py
def seed_requirements():
    rows = [
        ("Purchase Invoice", "supplier_invoice", "Supplier Invoice"),
    ]
    for doctype, key, label in rows:
        if not frappe.db.exists("AI Document Requirement",
                                {"target_doctype": doctype, "document_type_key": key}):
            frappe.get_doc({
                "doctype": "AI Document Requirement",
                "target_doctype": doctype,
                "document_type_key": key,
                "label": label,
                "is_active": 1,
            }).insert(ignore_permissions=True)
```

Or via **AI Document Requirement → New** in the desk.

## 5. Register Post-Processors (optional)

Auto-fill record fields after extraction:

```python
# your_app/handlers.py
def fill_purchase_invoice(extraction_result, doctype, docname, **kwargs):
    data = extraction_result.get("extracted_data", {})
    if not docname:
        return
    doc = frappe.get_doc(doctype, docname)
    doc.bill_no   = data.get("bill_no", doc.bill_no)
    doc.bill_date = data.get("bill_date", doc.bill_date)
    doc.save(ignore_permissions=True)
```

Register it:

```python
frappe.call(
    "frappe_intelligence.api.documents.register_post_processor",
    document_type_key="supplier_invoice",
    callback_method="your_app.handlers.fill_purchase_invoice",
)
```

See [WORKFLOWS.md](WORKFLOWS.md) for timing and security details.

## 6. Seed a Knowledge Pack (optional)

Inject domain knowledge into chat and agent prompts:

```python
def seed_knowledge():
    if frappe.db.exists("AI Knowledge Pack", {"pack_name": "My App Knowledge"}):
        return
    frappe.get_doc({
        "doctype": "AI Knowledge Pack",
        "pack_name": "My App Knowledge",
        "is_active": 1,
        "knowledge_entries": [
            {"topic": "Approval Policy",
             "content": "Purchase orders above 10,000 SAR require manager approval."},
        ],
    }).insert(ignore_permissions=True)
```

## 7. Build Workflows (optional)

For guided multi-step agent sessions, use **AI Workflow Builder** (desk → Workflow Builder). See [WORKFLOWS.md](WORKFLOWS.md).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Assistant not in the dock | `bench build --app frappe_intelligence`, then reload; the user must be allowed by AI Settings → Allowed Roles |
| "Cannot connect to Ollama" | `ollama serve` or switch to Claude in AI Settings |
| OCR returns empty | `bench pip install easyocr` |
| Voice transcription fails | `bench pip install faster-whisper` |
| Proactive bubble not showing | Create an AI Document Requirement for this DocType |
| Post-processor not running | Check `bench worker` is running; check Error Log for "unsafe callback" |
| "Too many requests" | User exceeded 20 calls / 60 s on an endpoint — wait, or change `REQUESTS_PER_MINUTE` in `utils/access.py` |
| Route map button does nothing | Route must start with `/app/` |
| Wrong language replies | Add Response Language rows in AI Settings → Chat tab |
| Assistant available to all users | Add rows to AI Settings → Assistant tab → Allowed Roles |
