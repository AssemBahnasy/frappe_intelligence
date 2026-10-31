# API Reference

All endpoints are called via `frappe.call` from the browser or `frappe.call` / direct import from Python. Each lives in the `api/` module named in its section: `frappe_intelligence.api.<module>.<endpoint>`.

| Module | Endpoints |
|---|---|
| `api.chat` | `send_message`, `stop_message`, `get_conversation`, `list_conversations`, `rate_reply`, `handle_widget_input` |
| `api.documents` | `process_document`, `get_log_status`, `confirm_extraction`, `submit_correction`, `list_templates`, `get_required_documents`, `register_post_processor` |
| `api.settings` | `get_widget_settings`, `get_route_map`, `test_connection`, `is_whatsapp_installed`, `is_whatsapp_enabled` |
| `api.builder` | `list_workflows`, `get_workflow_for_builder`, `save_workflow_builder`, `preview_step_prompt` |
| `api.portal` | `portal_chat`, `portal_upload_document`, `portal_get_session_state` |

## Access and rate limiting

Endpoints that reach a model require a desk user allowed by **AI Settings → Allowed Roles**. `send_message`, `handle_widget_input`, `process_document`, `portal_chat` and `portal_upload_document` are limited to **20 calls / user / 60 s** by Frappe's `rate_limit`. Details: [agent/security.md](agent/security.md).

---

## Chat (`api.chat`)

### `send_message`

Stores the message and answers it in a background job (Ask mode). POST only. The answer streams as `fi_assistant` realtime events; see [agent/live-replies.md](agent/live-replies.md).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `message` | str | ✓ | Max 4000 chars |
| `conversation` | str | ✗ | Omit to start a new conversation |
| `context` | object | ✗ | `{doctype, docname, tab, list_filters, route}` of the page the user is on |

```json
{"conversation": "a1b2c3d4e5", "run_id": "1bda4f3701d16586"}
```

### `stop_message`

Stops the running answer. POST only.

| Param | Type | Required |
|-------|------|----------|
| `conversation` | str | ✓ |
| `run_id` | str | ✓ |

### `get_conversation` / `list_conversations`

The user's own conversation as turns, and the user's recent desk conversations (`name`, `title`, `mode`, `modified`).

```json
{
  "name": "a1b2c3d4e5", "title": "How many Customer records are there?", "mode": "Ask", "active_run": null,
  "turns": [{
    "id": "row-name", "question": "How many Customer records are there?", "created": "2026-10-31 18:23:11",
    "steps": [{"label": "Counting Customer", "status": "done"}], "actions": [],
    "answer": "There are 3,423 Customer records.", "answer_id": "row-name", "feedback": null
  }]
}
```

### `rate_reply`

POST only. `conversation`, `message` (the turn's `answer_id`), `feedback`: `Good`, `Bad` or empty to clear.

---

## Document Processing (`api.documents`)

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

## Widget Input (`api.chat`)

### `handle_widget_input`

Entry point of the current widget for its three input modes; text and voice go through the agent loop, or through the workflow when `chat_mode="agent"`. The new panel uses `send_message`.

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
{"reply": "There are 2 Item records in the system.", "action": null, "action_data": null}

// voice response
{"transcript": "Show me all invoices", "reply": "…", "action": null}

// file response — same shape as process_document async result
```

---

## Templates & Documents (`api.documents`)

### `list_templates`

All active AI Document Templates.

```json
[{"name": "supplier_invoice", "document_name": "Supplier Invoice", "model_preference": "Both"}]
```

---

## Widget Settings (`api.settings`)

### `get_widget_settings`

Appearance, route map, allowed roles and whether the current user may use the assistant. Called on every page load.

```json
{
  "widget_color": "#6c63ff",
  "widget_icon": "",
  "assistant_name": "AI Assistant",
  "route_map": {"supplier_invoice": {"label": "Purchase Invoice", "route": "/app/purchase-invoice/new"}},
  "allowed_roles": [],
  "can_use": true
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

---

## Workflows (`api.builder`)

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

## Portal Endpoints (`api.portal`)

| Endpoint | Auth | Notes |
|----------|------|-------|
| `portal_chat` | Portal User table check | Workflow mode only; the workflow must be Active with Allow Portal |
| `portal_upload_document` | Portal User table check | Enqueues async job |
| `portal_get_session_state` | Portal User table check | Returns current step + collected data |

Rate limit: 20 / user / 60 s on `portal_chat` and `portal_upload_document`.
