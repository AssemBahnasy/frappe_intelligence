# Conversations (AI Conversation)

One DocType holds every conversation: desk chats and guided workflows on the desk, portal and WhatsApp.

| Field | Notes |
|---|---|
| `title` | First user message, set on save; a workflow's title |
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
| `off_topic` | A workflow redirect, written without AI ([../workflows/turn.md](../workflows/turn.md)) |
| `context` | Page the user was on |
| `attachments` | Files sent with a user message: `[{file_url, file_name}]` ([../documents/review.md](../documents/review.md)) |
| `raw`, `raw_provider` | The provider's own form of an assistant turn, replayed only to the same provider |
| `approval`, `preview` | Rows waiting for the user: `Pending`, `Approved`, `Rejected`, and the card they saw. A proposed change ([approvals.md](approvals.md)), or a document reading (`preview.kind = "review"`; `content` holds the reading until they confirm it) |

JSON values are stored as text because Frappe's JSON field rejects lists.

## History sent to the model

`AIConversation.provider_messages()`:

- skips error notices and `system` rows;
- sends the current user message and up to `HISTORY_LIMIT` (40) messages before it, plus the turn's own tool rows, however many; the window is counted up to the current question, so it holds still while the turn runs;
- always starts at a user message, so a tool result is never sent without its call;
- renders each user message with the caller's `user_content(text, context)`, so it goes back exactly as first sent.

The history must not change between turns. Claude binds its thinking blocks to everything sent before them, and rejects a replayed block if an earlier message differs. So:

| Case | What is sent |
|---|---|
| Whole history fits | Every assistant turn with its `raw`, thinking included |
| History trimmed | `raw` only for the current turn's replies; earlier ones are rebuilt from `content` and `tool_calls`, because their reasoning was made over messages no longer sent |
| `thinking=False` (workflows, whose instructions change every turn) | No `raw` at all |

If the history still changed (an edited **AI Settings → System Prompt** mid-conversation, a different set of tools), Claude answers again without the earlier reasoning; see [providers/interface.md](../providers/interface.md#replaying-provider-state).

## Permissions and retention

- **Desk User**: create, read, write, delete **own** conversations only. **System Manager**: all.
- Old conversations are deleted after 90 days through **Log Settings** (`default_log_clearing_doctypes` hook, `clear_old_logs`); change the period there.
- Idle workflow conversations become Abandoned after 7 days (`tasks.expire_old_sessions`).

Replies written without AI (a workflow's questions and redirects) are stored with `add_fixed_reply`; the model reads them as its own turns. A workflow's first row is its opening question, before any user message; the panel shows it as a turn without a question.
