# Workflows (`api.workflows`, `api.builder`)

## Guided workflows (`api.workflows`)

### `start_workflow`

POST only. `workflow`: an AI Workflow that is Active with Allow Desk. Creates the conversation with the first step's question asked and returns `{"conversation": name}`; answers go through `send_message`. See [workflows/desk.md](../workflows/desk.md).

### `exit_workflow`

POST only. `conversation`: the user's workflow conversation. Sets it Paused (only from Active); answering again continues from the same step. Refused while a reply is being written.

## Workflow Builder (`api.builder`)

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

Returns the workflow header, steps, knowledge packs, and the options for its selectors (packs, WhatsApp flows).

### `save_workflow_builder`

Saves the workflow header, its steps and its knowledge packs in one go. System Manager only.

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
