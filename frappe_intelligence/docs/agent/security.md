# Access, permissions and rate limits

## Who may use the assistant (`utils/access.py`)

Checked on the server by every endpoint that reaches a model (`ensure_assistant_access()`):

- not Guest;
- has the **Desk User** role (website and portal users use `api/portal.py` instead);
- has one of **AI Settings → Allowed Roles**, when that table is not empty.

`get_widget_settings` returns `can_use` so the widget can hide itself, but hiding is cosmetic; the server check is what protects.

## What the assistant may read or do

The agent acts as the signed-in user:

- Frappe MCP tools go through REST API v2 with the user's permissions, including user permissions and "if owner" rules.
- `run_report` uses `frappe.desk.query_report.run`, which checks the report and its reference DocType.
- `open_document` checks the DocType permission before saying whether a record exists.
- `new_document` checks create permission; nothing is saved without the user.
- Write tools exist only in Agent mode (off unless **AI Settings → Allow Agent Mode**), and `execute()` refuses a tool outside the conversation's mode even if a model asks for it.
- In Agent mode every change waits for the user's confirmation; see [approvals.md](approvals.md) for excluded DocTypes, the row lock and rollback.

## Document and workflow endpoints

| Endpoint | Check |
|---|---|
| `confirm_extraction`, widget file upload | Write permission on the record the result is linked to, before post-processors run |
| `workflow_reply` (desk, portal, WhatsApp) | The workflow is Active and allowed on that channel (`allow_desk`, `allow_portal`, `allow_whatsapp`) |
| `test_connection` | System Manager |

## Rate limits

Frappe's `rate_limit` decorator (`utils/access.limit_requests`): 20 requests per minute per user and endpoint, counted atomically in Redis. Applied to `send_message`, `handle_widget_input`, `process_document`, `portal_chat` and `portal_upload_document`.

## Removed in step 2

| Removed | Why |
|---|---|
| `debug_chat` | Returned tracebacks and spent tokens |
| `create_document` | Inserted records with no preview; replaced by `new_document` now and approvals in step 5 |
| `clear_chat_history` and Redis chat history | Conversations are stored in AI Conversation |
| Location answer from processing logs | Returned coordinates of records the user could not read |
| `search_records` | Listed names past record-level permissions; replaced by `list_documents` |
