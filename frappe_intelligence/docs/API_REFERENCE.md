# API Reference

All endpoints are called via `frappe.call` from the browser or `frappe.call` / direct import from Python. Each lives in the `api/` module named in its section: `frappe_intelligence.api.<module>.<endpoint>`.

| Module | Endpoints |
|---|---|
| `api.chat` | `send_message`, `decide_proposal`, `stop_message`, `get_conversation`, `list_conversations`, `rate_reply` |
| `api.documents` | `process_document`, `get_log_status`, `confirm_extraction`, `submit_correction`, `list_templates`, `get_required_documents`, `register_post_processor` |
| `api.settings` | `test_connection`, `is_whatsapp_installed`, `is_whatsapp_enabled` |
| `api.workflows` | `start_workflow`, `exit_workflow` |
| `api.writer` | `write_field` |
| `api.voice` | `transcribe` |
| `api.jobs` | `job_result` |
| `api.builder` | `list_workflows`, `get_workflow_for_builder`, `save_workflow_builder`, `preview_step_prompt` |
| `api.portal` | `portal_chat`, `portal_upload_document`, `portal_get_session_state` |

## Access and rate limiting

Endpoints that reach a model require a desk user allowed by **AI Settings → Allowed Roles**. `send_message`, `start_workflow`, `write_field`, `transcribe`, `process_document`, `portal_chat` and `portal_upload_document` are limited to **20 calls / user / 60 s** by Frappe's `rate_limit`. Details: [agent/security.md](agent/security.md).

---

## Chat (`api.chat`)

### `send_message`

Stores the message and answers it in a background job. POST only. In a workflow conversation the message is the user's answer and `mode` is ignored. The answer streams as `fi_assistant` realtime events; see [agent/live-replies.md](agent/live-replies.md).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `message` | str | ✓ | Max 4000 chars; may be empty when files are attached |
| `conversation` | str | ✗ | Omit to start a new conversation |
| `context` | object | ✗ | `{doctype, docname, new, tab, list_filters, route}` of the page the user is on |
| `mode` | str | ✗ | `Ask` (default) or `Agent`; Agent needs **Allow Agent Mode** |
| `attachments` | list | ✗ | Up to 3 file URLs the user may read; read before the model answers ([documents/review.md](documents/review.md)) |

```json
{"conversation": "a1b2c3d4e5", "run_id": "1bda4f3701d16586"}
```

### `decide_proposal`

Confirms or rejects a change proposed in Agent mode, or confirms or discards a document reading. POST only.

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `conversation` | str | ✓ | |
| `call_id` | str | ✓ | |
| `approve` | bool | ✓ | |
| `values` | object | ✗ | A document reading's fields as the user left them, `{field_key: value}` |

Returns `{"run_id": …}` once no change is left waiting (the answer continues in the background), or `{"run_id": null}` while others still wait. See [agent/approvals.md](agent/approvals.md).

### `stop_message`

Stops the running answer. POST only.

| Param | Type | Required |
|-------|------|----------|
| `conversation` | str | ✓ |
| `run_id` | str | ✓ |

### `get_conversation` / `list_conversations`

The user's own conversation as turns, and the user's recent desk conversations, workflows included (`name`, `title`, `mode`, `modified`). A workflow conversation also returns `workflow`: `{title, status, step, steps, step_label, answers: [{label, value}], missing: [label], choices: [str]}`; other conversations return `null`.

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

## Guided workflows (`api.workflows`)

### `start_workflow`

POST only. `workflow`: an AI Workflow that is Active with Allow Desk. Creates the conversation with the first step's question asked and returns `{"conversation": name}`; answers go through `send_message`. See [workflows/desk.md](workflows/desk.md).

### `exit_workflow`

POST only. `conversation`: the user's workflow conversation. Sets it Paused (only from Active); answering again continues from the same step. Refused while a reply is being written.

---

## Write with AI (`api.writer`)

### `write_field`

POST only. Writes one long text field in the background and returns `{"job": id}`; the text is the job's value (see [Background jobs](#background-jobs-apijobs)). See [writer/server.md](writer/server.md).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `doctype` | str | ✓ | |
| `fieldname` | str | ✓ | Small Text, Text, Long Text, Text Editor or Markdown Editor, editable by the user |
| `instruction` | str | ✓ | What the field should say; up to 2000 characters |
| `current` | str | ✗ | The field's current text |
| `context` | object | ✗ | The form's other values by field name; only readable fields are used |
| `docname` | str | ✗ | Omit on a new form |

## Voice input (`api.voice`)

### `transcribe`

POST only. `file_url`: a recording the user just uploaded as a private File. Turns it into text in the background (Whisper, on this server) and returns `{"job": id}`; the text is the job's value. The recording is deleted afterwards. Refused when the voice package is not installed. See [panel/voice.md](panel/voice.md).

## Background jobs (`api.jobs`)

Write with AI and voice input run as short background jobs (`utils/background.py`). The result arrives on the `fi_job` realtime event as `{job, value}` or `{job, error}`.

### `job_result`

`job`: a job the user started. Returns `{value}`, `{error}` or `{pending: true}`; for a browser that missed the event.

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

## Templates & Documents (`api.documents`)

### `list_templates`

All active AI Document Templates.

```json
[{"name": "supplier_invoice", "document_name": "Supplier Invoice", "model_preference": "Both"}]
```

---

## Required documents (`api.documents`)

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

Workflows for the Workflow Builder's picker.

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
