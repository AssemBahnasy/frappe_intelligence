# Agent mode and approvals

In Agent mode the assistant can create, update, submit, cancel and delete documents. Every change is shown as a card (approved board 2c) and runs only after the user confirms it.

## Turning it on

**AI Settings → Widget → Agent Mode**

| Field | Notes |
|---|---|
| Allow Agent Mode | Off by default. Without it the panel shows Agent as disabled and `send_message(mode="Agent")` is refused |
| Excluded DocTypes | DocTypes the assistant must never change. Users, roles, permissions, System Settings, AI Settings and AI Conversation are always excluded (`changes.ALWAYS_EXCLUDED`) |

The mode is chosen in the panel's mode menu and stored on the conversation; it can change between messages.

## Flow

```
model calls create_document(...)
  → changes.preview_create: same argument check as Frappe's MCP server, excluded DocTypes,
    the user's create/write/delete/submit/cancel permission → card
      invalid → the error goes back to the model to fix, no card
  → AI Conversation: tool row with approval "Pending" and the card in `preview`
  → the turn pauses; `done` carries `proposals`

user clicks Confirm / Reject → api.chat.decide_proposal (row lock on the conversation)
  → row approval "Approved" / "Rejected" (rejected rows get a result telling the model)
  → when nothing is left waiting: a new background run
      → approved changes run first (agent/loop._run_approved), each in a savepoint
      → the model reports back with the results
```

Sending a new message while a card is waiting rejects it ("The user did not confirm this change…").

## Tools (`agent/tools/changes.py`, Agent mode only)

| Tool | Runs through | Card |
|---|---|---|
| `create_document` | Frappe MCP (`REST v2 create_doc`) | The values with field labels; "Saved as Draft. You submit it." on submittable DocTypes |
| `update_document` | Frappe MCP (`update_doc`) | The new values |
| `delete_document` | Frappe MCP (`delete_doc`) | The document |
| `submit_document` | `doc.submit()` after `check_permission("submit")`, drafts only | The document |
| `cancel_document` | `doc.cancel()` after `check_permission("cancel")`, submitted only | The document |

## Safety

| Risk | Guard |
|---|---|
| A change runs without the user | Write tools have a `preview`; the loop never calls their `run` while proposing |
| Double click runs it twice | `decide_proposal` locks the conversation row; a decided row cannot be decided again |
| Half-made change | Each run happens in a savepoint, rolled back if it fails; the result is committed together with the change |
| Worker dies after the change | The change and its result share one transaction, so neither stays; the row is still Approved and empty, and the next run makes it |
| Settings change before Confirm | Agent mode and Excluded DocTypes are checked again when the change runs; it then fails with the reason |
| Ask mode | Write tools are not offered, and `execute` refuses them even if a model asks |

## In the conversation

Proposal rows are tool rows with `approval` (`Pending`, `Approved`, `Rejected`) and `preview`. Pending rows are never sent to the model. The transcript turns them into `proposals`: `pending`, `approved` (running), `done` (with the created document's name), `failed` (with the error) or `rejected`.
