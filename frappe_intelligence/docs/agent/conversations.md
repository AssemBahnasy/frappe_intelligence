# Conversations (AI Conversation)

One DocType holds every conversation: desk chats and guided workflows on the desk, portal and WhatsApp.

| Field | Notes |
|---|---|
| `title` | First user message, set on save |
| `mode` | `Ask`, `Agent`, `Workflow` |
| `status` | `Active`, `Completed`, `Abandoned`, `Paused` (workflows) |
| `channel`, `channel_id` | `Desk`, `Portal`, `WhatsApp`; portal user or phone number |
| `last_user_message_at` | Drives WhatsApp's 24-hour reply window |
| `workflow`, `current_step`, `collected_data` | Workflow state |
| `linked_doctype`, `linked_docname` | Record the conversation is about |
| `messages` | **AI Conversation Message** rows |

## Messages

| Field | Notes |
|---|---|
| `role` | `user`, `assistant`, `tool`, `system` |
| `content` | What the user typed, the model's text, or a tool result (JSON) |
| `tool_calls` | Assistant turns: `[{id, name, arguments}]` |
| `tool_name`, `tool_call_id` | Tool turns |
| `is_error` | Error notices (never sent to the model) and failed tool results (sent, so the model can recover) |
| `context` | Page the user was on |
| `raw`, `raw_provider` | The provider's own form of an assistant turn, replayed only to the same provider |

JSON values are stored as text because Frappe's JSON field rejects lists.

## History sent to the model

`AIConversation.provider_messages()`:

- skips error notices and `system` rows;
- sends the last `HISTORY_LIMIT` (40) messages, extended back to the current user message on long multi-tool turns;
- always starts at a user message, so a tool result is never sent without its call.

## Permissions and retention

- **Desk User**: create, read, write, delete **own** conversations only. **System Manager**: all.
- Old conversations are deleted after 90 days through **Log Settings** (`default_log_clearing_doctypes` hook, `clear_old_logs`); change the period there.
- Idle workflow conversations become Abandoned after 7 days (`tasks.expire_old_sessions`).
