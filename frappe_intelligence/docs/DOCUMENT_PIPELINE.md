# Document Pipeline

The document pipeline reads a file, classifies it against a template, extracts labelled fields, and delivers the result to the browser — all asynchronously.

## Document Templates

**AI Document Template** defines one document type:

| Field | Purpose |
|-------|---------|
| `document_type_key` | Unique slug (e.g. `supplier_invoice`) — used in API calls and requirements |
| `document_name` | Human-readable label |
| `model_preference` | `Heuristic`, `VLM`, or `Both` (run both, merge results) |
| `is_active` | Inactive templates are excluded from classification |
| `detection_keywords` | Comma-separated words; scored against extracted text to pick the right template |

Templates ship with **no defaults** — define yours via the desk or a bundle file.

## Extraction Rules

Each **AI Extraction Rule** child row defines one field to extract:

| Field | Notes |
|-------|-------|
| `field_key` | Snake_case identifier (e.g. `vat_number`) — used as key in `extracted_data` |
| `label` | Display label |
| `extraction_strategy` | `Regex`, `VLM`, or `Both` |
| `regex_pattern` | Python regex; matched against full raw text; first capture group used if present |
| `llm_hint` | Natural-language instruction passed to the LLM for this field |

### Strategy Logic

| Strategy | How |
|----------|-----|
| `Regex` | Match `regex_pattern` against raw text — no LLM call |
| `VLM` | Pass `llm_hint` to the configured AI provider (`documents/extractor.py`) |
| `Both` | Run regex first; fall back to LLM if regex returns `None` |

Use `Both` as the default — fast when regex matches, accurate fallback when it doesn't.

### Confidence Score

`confidence_score = matched_fields / total_fields`.

Below `confidence_threshold` (global or per-workflow, `documents/review.confidence_threshold`) → the reading is marked for review. Template matching and extraction live in `documents/templates.py`; the panel's review is in [documents/review.md](documents/review.md).

## Seeding Templates from a Bundle

For app-level seeding, define templates in a JSON bundle and call `seed_template_bundle()` from `after_install`.

### Bundle Format

```json
{
  "templates": [
    {
      "document_type_key": "supplier_invoice",
      "document_name": "Supplier Invoice",
      "model_preference": "Both",
      "detection_keywords": "invoice, فاتورة, supplier, bill",
      "extraction_rules": [
        {
          "field_key": "bill_no",
          "label": "Invoice Number",
          "extraction_strategy": "Both",
          "regex_pattern": "(?:Invoice|Inv|فاتورة)[\\s#:]*([A-Z0-9-]+)",
          "llm_hint": "Extract the invoice number or reference number."
        },
        {
          "field_key": "vat_number",
          "label": "VAT Number",
          "extraction_strategy": "Regex",
          "regex_pattern": "(?:VAT|ضريبة|الرقم الضريبي)[\\s:]*([0-9]{15})"
        }
      ]
    }
  ]
}
```

### Calling from after_install

```python
from frappe_intelligence.utils.seed_manager import seed_template_bundle
import os

def after_install():
    bundle_path = os.path.join(os.path.dirname(__file__), "data", "templates.json")
    seed_template_bundle(bundle_path)
```

`seed_template_bundle` is idempotent — it skips templates that already exist (preserves desk customizations).

## Classification

When `target_doctype=None` (Auto-detect):

1. Extract raw text from the file
2. Score each active template's `detection_keywords` against the text
3. Select the highest-scoring template
4. If no template scores above 0, return `status: "failed"`

When `target_doctype="supplier_invoice"` (explicit):
- Bypass keyword scoring, resolve template directly by `document_type_key`

## File Reading

| File type | Method |
|-----------|--------|
| PDF (digital text) | pypdf — lossless text extraction per page |
| Images (png, jpg, bmp, tiff, webp) | EasyOCR — Arabic + English |
| Scanned PDF | EasyOCR on rendered page images |
| Plain text | UTF-8 read |

Security: `validate_file_access()` checks that the file URL starts with `/files/` or `/private/files/`, the resolved path stays within the site directory, and the current user has read permission on private files.

## Training Pairs

When a user edits extraction results in the review panel, an **AI Training Pair** is created automatically:

| Field | Content |
|-------|---------|
| `document_template` | Template that produced the extraction |
| `processing_log` | Source log |
| `session` | Agent session (if triggered via chat/agent channel) |
| `original_extraction` | Raw `extracted_data` from the log |
| `corrected_extraction` | User's edited values |
| `correction_source` | User email |

Training pairs are not fed back to the LLM automatically. Use them to:
1. Spot systematic extraction errors (wrong regex, vague LLM hint)
2. Improve `regex_pattern` or `llm_hint` on the template
3. Adjust `detection_keywords` if misclassification is the issue

Mark `applied=1` once you've acted on a correction to track which pairs have been addressed.

## Processing Log

**AI Processing Log** records every pipeline run:

| Field | Notes |
|-------|-------|
| `processing_status` | `Pending` → `Processing` → `Completed` / `Failed` |
| `confidence_score` | 0.0–1.0 |
| `extracted_data` | JSON — field_key → value |
| `raw_text` | Full OCR/PDF output |
| `session` | Agent session if triggered via chat channel |
| `linked_doctype` / `linked_docname` | Record the result was linked to |

Logs are readable by the user who triggered the extraction and by System Managers.
