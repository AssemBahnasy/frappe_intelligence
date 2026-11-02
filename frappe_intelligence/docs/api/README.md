# API

Whitelisted endpoints, one file per `api/` module: `frappe_intelligence.api.<module>.<endpoint>`, called with `frappe.call` from the browser or imported from Python.

| Module | Endpoints | Doc |
|---|---|---|
| `api.chat` | `send_message`, `decide_proposal`, `stop_message`, `get_conversation`, `list_conversations`, `rate_reply` | [chat.md](chat.md) |
| `api.workflows`, `api.builder` | `start_workflow`, `exit_workflow`; `list_workflows`, `get_workflow_for_builder`, `save_workflow_builder`, `preview_step_prompt` | [workflows.md](workflows.md) |
| `api.writer`, `api.voice`, `api.jobs` | `write_field`, `transcribe`, `job_result` | [jobs.md](jobs.md) |
| `api.documents` | `process_document`, `get_log_status`, `confirm_extraction`, `submit_correction`, `list_templates`, `get_required_documents`, `register_post_processor` | [documents.md](documents.md) |
| `api.tutorial` | `set_done` | [tutorial.md](tutorial.md) |
| `api.settings` | `test_connection`, `is_whatsapp_installed`, `is_whatsapp_enabled` | [settings.md](settings.md) |
| `api.portal` | `portal_chat`, `portal_upload_document`, `portal_get_session_state` | [portal.md](portal.md) |

## Access and rate limits

Endpoints that reach a model require a desk user allowed by **AI Settings → Allowed Roles**. `send_message`, `decide_proposal`, `start_workflow`, `write_field`, `transcribe`, `process_document`, `portal_chat` and `portal_upload_document` are limited to 20 calls a minute per user and endpoint by Frappe's `rate_limit` (per IP address on Frappe releases without per-user limits). Details: [../agent/security.md](../agent/security.md).

Endpoints only check access and inputs, then hand over to a feature module ([../guidelines/code.md](../guidelines/code.md)).
