# Documents (`api.documents`)

The document pipeline for the portal, WhatsApp and other apps ([../documents/pipeline.md](../documents/pipeline.md)). The panel reads attached files through the agent instead ([../documents/review.md](../documents/review.md)).

## Processing

### `process_document`

Enqueues a document for OCR + LLM extraction. Returns immediately.

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `file_url` | str | ✓ | Must start with `/files/` or `/private/files/` |
| `target_doctype` | str\|null | ✗ | `document_type_key` or `null` for auto-detect |

```json
// immediate response
{"status": "queued", "log_name": "AI-PROC-LOG-00001"}

// async result via ai_processing_complete realtime event
{
  "status": "success",
  "document_type_key": "supplier_invoice",
  "extracted_data": {"bill_no": "INV-001", "bill_date": "2024-05-15"},
  "confidence_score": 0.87,
  "log_name": "AI-PROC-LOG-00001",
  "needs_review": false
}
```

### `get_log_status`

Polling fallback when the realtime event is not received. Access: log owner or System Manager.

| Param | Type | Required |
|-------|------|----------|
| `log_name` | str | ✓ |

```json
// while processing
{"status": "Processing", "result": null}

// on completion — result shape identical to ai_processing_complete payload
{"status": "Completed", "result": {...}}
```

### `confirm_extraction`

Accept a low-confidence result and fire post-processors. Access: log owner or System Manager.

| Param | Type | Required |
|-------|------|----------|
| `log_name` | str | ✓ |
| `doctype` | str | ✗ |
| `docname` | str | ✗ |

```json
{"ok": true}
```

### `submit_correction`

Save a user correction as an AI Training Pair. Access: log owner or System Manager.

| Param | Type | Required |
|-------|------|----------|
| `log_name` | str | ✓ |
| `corrected_extraction` | dict | ✓ |

```json
{"training_pair": "AI-TRAIN-00001"}
```

## Templates

### `list_templates`

All active AI Document Templates.

```json
[{"name": "supplier_invoice", "document_name": "Supplier Invoice", "model_preference": "Both"}]
```

## Required documents

### `get_required_documents`

Present/missing required documents for a record.

| Param | Type | Required |
|-------|------|----------|
| `doctype` | str | ✓ |
| `docname` | str | ✓ |

```json
{
  "present": [{"document_type_key": "cr", "label": "CR Certificate"}],
  "missing": [{"document_type_key": "vat_cert", "label": "VAT Certificate"}]
}
```

## Post-processors

### `register_post_processor`

Register a Python callback for a document type. System Manager only.

| Param | Type | Required |
|-------|------|----------|
| `document_type_key` | str | ✓ |
| `callback_method` | str | ✓ | Must be in an installed Frappe app |
| `description` | str | ✗ |

```json
{"name": "AI-POST-PROC-00001"}
```
