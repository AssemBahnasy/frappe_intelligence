# Templates and extraction

An **AI Document Template** describes one kind of document and the fields read from it. The app ships with none: define them in the desk or seed them from a bundle.

## Template

| Field | Purpose |
|---|---|
| Document Type Key | Unique slug (`supplier_invoice`), also the record's name; used by API calls and requirements |
| Document Name | The title shown on the review card |
| Model Preference | Who extracts: `Heuristic` (regex rules only, no AI), `VLM` (the AI provider for every rule), `Both` (regex first, the AI for what it missed) |
| Is Active | Inactive templates are never matched |
| Detection Keywords | Comma-separated words; the template whose words the text contains most is chosen |

## Extraction rules

One **AI Extraction Rule** row per field:

| Field | Purpose |
|---|---|
| Field Key | The key in the extracted values (`bill_no`); use the target DocType's field name so the values fill its form |
| Label | Shown on the review card |
| Extraction Strategy | `Regex` (needs a pattern), `VLM` (needs a hint), `Both` |
| Regex Pattern | Matched against the whole text; the first capture group is the value |
| LLM Hint | What the AI should look for |

**Confidence** is the share of regex-capable rules that matched. Below **AI Settings → Confidence Threshold** (or the workflow's own) the reading is marked "Review needed".

## Extraction mode

**AI Settings → Extraction Mode** decides how the AI reads the fields it is asked for (`documents/extractor.py`):

| Mode | Model calls | Suits |
|---|---|---|
| Per Field | One per field | Small or unstable models |
| Batch | One for all fields | Strong models |
| Batch with Fallback (default) | One batch, then one per field it missed | Most setups |
| Parallel | One per field, at the same time | Mid-range servers |

## Matching

`documents/templates.match(text, key=None)`: the active template named by `key`, else the one with the most detection keywords in the text, else none (the assistant then works from the text alone).

## Files read

`documents/reader.py`: embedded PDF text (PyMuPDF or pypdf), plain text files, and photos or scanned PDF pages through EasyOCR (Arabic and English) when the `ocr` extra is installed. File URLs are checked by `utils/file_utils.validate_file_access`: under `/files/` or `/private/files/`, inside the site folder, readable by the user.

## Bundle format

Seeded with `utils/seed_manager.seed_template_bundle(path)` ([../setup/integration.md](../setup/integration.md#seeding-templates)):

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
          "llm_hint": "The invoice or reference number."
        }
      ]
    }
  ]
}
```
