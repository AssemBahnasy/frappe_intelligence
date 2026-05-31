# API Reference

All endpoints are called via `frappe.call` from the browser or `frappe.call` / direct import from Python.

## Rate Limiting

Rate-limited endpoints: `process_document`, `handle_widget_input`, `test_connection`
Limit: **20 calls / user / 60 s** using a Redis counter (`fi_rl:{user}`).
Exceeding the limit raises `RateLimitExceededError`.

---

## Document Processing

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

---

## Widget Input

### `handle_widget_input`

Unified entry-point for all three widget input modes. Rate-limited.

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `input_type` | str | ✓ | `"file"` / `"voice"` / `"text"` |
| `file_url` | str | for file/voice | Must start with `/files/` or `/private/files/` |
| `text_input` | str | for text | Max 4000 chars |
| `doctype` | str | ✗ | Context hint for schema injection |
| `docname` | str | ✗ | Context hint |
| `widget_mode` | str | ✗ | `"desk"` / `"portal"` |
| `chat_mode` | str | ✗ | `"ask"` / `"agent"` |
| `workflow_key` | str | ✗ | Required when `chat_mode="agent"` |

```json
// text response
{"reply": "Here are 3 matching customers…", "action": "search_results", "action_data": {...}}

// voice response
{"transcript": "Show me all invoices", "reply": "…", "action": null}

// file response — same shape as process_document async result
```

---

## Templates & Documents

### `list_templates`

All active AI Document Templates.

```json
[{"name": "supplier_invoice", "document_name": "Supplier Invoice", "model_preference": "Both"}]
```

### `create_document`

Create a Frappe document and return its name and route. Child tables auto-detected via `frappe.get_meta()`.

| Param | Type | Required |
|-------|------|----------|
| `doctype` | str | ✓ |
| `values` | str (JSON) | ✓ |

```json
{"name": "SI-00001", "route": "/app/sales-invoice/si-00001"}
```

---

## Widget Settings

### `get_widget_settings`

Appearance, route map, and allowed roles. Called on every page load.

```json
{
  "widget_color": "#6c63ff",
  "widget_icon": "",
  "assistant_name": "AI Assistant",
  "route_map": {"supplier_invoice": {"label": "Purchase Invoice", "route": "/app/purchase-invoice/new"}},
  "allowed_roles": []
}
```

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

### `clear_chat_history`

Clear Redis chat history for the current session.

```json
{"ok": true}
```

---

## Workflows

### `list_workflows`

Active workflows for the widget workflow selector.

```json
[{"workflow_key": "service_request", "title": "Service Request"}]
```

### `get_workflow_for_builder`

Full builder state payload. System Manager only.

| Param | Type |
|-------|------|
| `workflow_key` | str |

Returns workflow header, steps, requirements, knowledge_packs, post_processors, and available options for all selectors.

### `save_workflow_builder`

Atomically upsert workflow + steps + requirements + pack/processor assignments. System Manager only.

| Param | Type |
|-------|------|
| `workflow_key` | str |
| `payload` | str (JSON) |

```json
{"ok": true}
```

### `preview_step_prompt`

Render the LLM prompt for an unsaved step draft. System Manager only.

| Param | Type |
|-------|------|
| `step_data` | dict |

```json
{"prompt": "System: You are a concierge...\nUser: ..."}
```

---

## Post-Processors

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

---

## Feature Gates

### `is_whatsapp_installed`

```json
true
```

### `is_whatsapp_enabled`

```json
true
```

---

## Connection

### `test_connection`

Ping the active AI provider. System Manager only. Rate-limited.

```json
{"ok": true}
// or
{"ok": false, "error": "Cannot connect to Ollama at http://localhost:11434"}
```

---

## Portal Endpoints (`api_portal.py`)

| Endpoint | Auth | Notes |
|----------|------|-------|
| `portal_chat` | Portal User table check | Always agent mode; no FRAPPE_TOOLS |
| `portal_upload_document` | Portal User table check | Enqueues async job |
| `portal_get_session_state` | Portal User table check | Returns current step + collected data |

Rate limit: `fi_rl_portal:{customer}`, 20 / 60 s.
