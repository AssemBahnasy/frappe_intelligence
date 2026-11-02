# Structure

The panel follows the frappe-vue architecture: a host loads a bundle with `frappe.require`, a plain class mounts the Vue app with its own Pinia, and `destroy()` unmounts it.

```
fi_launcher.bundle.js                                 always loaded (app_include_js)
  → frappe.require("fi_assistant.bundle.js")          once, shared promise
      → new frappe_intelligence.ui.AssistantPanel()   assistant/panel.js
          → <aside class="fi-assistant"> appended to <body>
          → createApp(Panel) · SetVueGlobals · createPinia
```

| File | Responsibility |
|---|---|
| `public/js/fi_launcher.bundle.js` | Dock button, sidebar row, Ctrl+., open state across reloads |
| `public/css/fi_launcher.bundle.css` | Docks the `<aside>` in the desk's flex row; active launcher; phone layout |
| `public/js/fi_assistant.bundle.js` | Exposes `frappe_intelligence.ui.AssistantPanel` |
| `assistant/panel.js` | Host class: open, close, toggle, destroy |
| `assistant/store.js` | Pinia store: conversation, turns, the running answer, `fi_assistant` events, history, feedback, workflow progress |
| `assistant/page_context.js` | The page sent as context and the chip label |
| `assistant/actions.js` | Browser actions (`set_route`, `open_form`, `new_doc`, `fill_form`) |
| `assistant/tables.js` | Sortable, paged tables in answers; number columns at the end |
| `assistant/bidi.js` | Numbers and codes isolated inside right-to-left answers |
| `assistant/voice.js` | Recording and transcribing voice input |
| `assistant/uploads.js` | Uploading attached files and recordings |
| `shared/background.js` | Waiting for a background job's result (also used by Write with AI) |
| `assistant/components/` | `Panel`, `MessageList`, `Turn`, `Steps`, `ChartBlock`, `EmptyState`, `Composer`, `Icon`, `Card`, `ProposalCard`, `ReviewCard`, `ChangeResult`, `FileChip`, `WorkflowBar` |

## Server side

| Piece | Responsibility |
|---|---|
| `boot.py` | `frappe.boot.fi_assistant` for allowed users, with the workflows they can start |
| `agent/suggestions.py` | Starter questions by role |
| `agent/transcript.py` | Stored rows → turns with steps, answer, actions, feedback, stopped |
| `api/chat.py` | `send_message`, `decide_proposal`, `stop_message`, `get_conversation`, `list_conversations`, `rate_reply` |
| `api/workflows.py` | `start_workflow`, `exit_workflow` |
| `api/voice.py`, `api/jobs.py` | `transcribe`; `job_result` |
| `workflows/desk.py` | Startable workflows; the workflow bar's progress and quick replies |

## Notes

- The store listens to route changes through `$(document).on("page-change.fi_assistant")`, not `frappe.router.on`, whose `off()` cannot remove a handler (`frappe/event_emitter.js`).
- `frappe.get_route()` is `null` when the desk starts, before the router runs; `page_context` handles it.
- Component styles are scoped and ship inside the JS bundle. The launcher CSS is a `.bundle.css`, so Frappe builds its right-to-left copy.
