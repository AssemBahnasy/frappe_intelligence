# Chat (`api.chat`)

## `send_message`

Stores the message and answers it in a background job. POST only. In a workflow conversation the message is the user's answer and `mode` is ignored. The answer streams as `fi_assistant` realtime events; see [agent/live-replies.md](../agent/live-replies.md).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `message` | str | ✓ | Max 4000 chars; may be empty when files are attached |
| `conversation` | str | ✗ | Omit to start a new conversation |
| `context` | object | ✗ | `{doctype, docname, new, tab, list_filters, route}` of the page the user is on |
| `mode` | str | ✗ | `Ask` (default) or `Agent`; Agent needs **Allow Agent Mode** |
| `attachments` | list | ✗ | Up to 3 file URLs the user may read; read before the model answers ([documents/review.md](../documents/review.md)) |

```json
{"conversation": "a1b2c3d4e5", "run_id": "1bda4f3701d16586"}
```

## `decide_proposal`

Confirms or rejects a change proposed in Agent mode, or confirms or discards a document reading. POST only.

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `conversation` | str | ✓ | |
| `call_id` | str | ✓ | |
| `approve` | bool | ✓ | |
| `values` | object | ✗ | A document reading's fields as the user left them, `{field_key: value}` |

Returns `{"run_id": …}` once no change is left waiting (the answer continues in the background), or `{"run_id": null}` while others still wait. See [agent/approvals.md](../agent/approvals.md).

## `stop_message`

Stops the running answer. POST only.

| Param | Type | Required |
|-------|------|----------|
| `conversation` | str | ✓ |
| `run_id` | str | ✓ |

## `get_conversation` / `list_conversations`

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

## `rate_reply`

POST only. `conversation`, `message` (the turn's `answer_id`), `feedback`: `Good`, `Bad` or empty to clear.
