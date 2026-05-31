# Widget Guide

The Intelligence Concierge widget is injected automatically into every Frappe Desk page via `app_include_js`. No setup needed for end-users.

## FAB (Floating Action Button)

- Default position: bottom-left (LTR) / bottom-right (RTL) — 24 px from edges
- Draggable — position persists in `localStorage` key `fi_widget_pos`
- Panel opens on the opposite side of the screen from the FAB position
- RTL-aware: mirrors direction from `<html dir>`

## Input Modes

| Mode | How | Backend call |
|------|-----|-------------|
| **Upload** | Select a doc type from the checklist, pick a file | `process_document` → background OCR + LLM |
| **Chat** | Type in the chat panel | `handle_widget_input(input_type="text")` |
| **Voice** | Press mic, speak, release | `handle_widget_input(input_type="voice")` → Whisper → LLM |

### Upload Flow

1. Pick doc type (or Auto-detect) → select file
2. Widget POSTs file to `/api/method/upload_file` → shows upload progress
3. Calls `process_document` → returns `{"status": "queued"}` immediately
4. Shows "Processing in background…" spinner
5. Receives `ai_processing_complete` via Socket.io → displays result
6. **Polling fallback:** if no Socket.io event in 5 s → polls `get_log_status` every 5 s

Auto-detect sends `null` as `target_doctype`, triggering keyword-based classification.

### Low-Confidence Review

When `confidence_score < confidence_threshold`:
- Widget shows editable Review panel instead of accepting
- **Discard** — close without firing post-processors
- **Accept** — if fields edited: saves training pair first, then fires post-processors; if unchanged: fires post-processors immediately

## Chat Modes

The chat panel has two modes, selectable via the toggle at the top:

| Mode | Behaviour |
|------|-----------|
| **Ask** | Free-form chat with RAG, tool use, streaming; no workflow scope enforcement |
| **Agent** | Workflow-guided; scope enforced before LLM; step-by-step data collection |

In Agent mode, select the workflow from the dropdown. Only active workflows with `allow_desk=1` appear.

## Streaming

AI replies stream token-by-token via Socket.io (`ai_stream_chunk`):
- Typing indicator `…` replaced by first token on arrival
- Tokens appended in-place — no flicker
- If the model calls a tool (navigate, search, etc.) instead of streaming text, the action button appears after the full HTTP response

## Multi-turn Memory

Chat history is stored in Redis per Frappe session (TTL 2 h, capped at 20 messages). The AI sees full conversation context on every message. Click **↺** in the chat header to start a new conversation.

## Agentic Actions

When the AI calls a built-in Frappe tool:

| Tool | Widget renders | On click |
|------|---------------|---------|
| `navigate` | Labelled button | `frappe.set_route()` |
| `open_record` | Record name button | `frappe.set_route()` to form view |
| `create_record` | DocType name button | Calls `create_document` → navigates to saved record |
| `search_results` | Inline list of record links | Each link navigates to form view |

URL slugs use hyphens (`/app/sales-invoice/si-00001`). `frappe.scrub()` is intentionally not used for URL building (it produces underscores that cause 404 errors).

## Proactive Bubble

Shown on Form pages when the record has missing required documents (configured via AI Document Requirement). Reads "{N} missing document(s)" and opens the Smart Checklist on click.

## Realtime Events

| Event | Source | Widget action |
|-------|--------|--------------|
| `ai_processing_update` | Any background code | Updates spinner text |
| `ai_processing_complete` | RQ worker | Shows extraction result |
| `ai_stream_chunk` | LLM adapter | Appends token to chat bubble |

Publish custom progress messages from your own background jobs:
```python
frappe.publish_realtime("ai_processing_update", {"message": "Step done"}, user=frappe.session.user)
```

## Access Control

**AI Settings → Widget tab → Allowed Roles** — list Frappe roles that can see the widget. Empty = all users. Widget removes itself from the DOM silently for unauthorized users. Cached 1 h in Redis.

## Appearance

All appearance fields are in **AI Settings → Widget tab**. See [CONFIGURATION.md](CONFIGURATION.md).

## Internationalisation

All visible strings use Frappe's `__()`. Arabic ships in `translations/ar.csv` (116 strings). To add a language:

```csv
Intelligence Concierge,مساعد الذكاء الاصطناعي
```

Save to `frappe_intelligence/translations/<lang>.csv`, then `bench build --app frappe_intelligence`.

## JavaScript Module Structure

```
public/js/widget/
  widget.js      composition entry — Object.assign() all modules + init()
  dom.js         _buildDOM(), _injectStyles()
  events.js      _bindEvents(), _bindRealtime()
  settings.js    _applySettings(), page watcher, context check
  ui.js          FAB drag, panel state machine, progress helpers
  chat.js        text command flow, action buttons, search results
  upload.js      upload panel, checklist, XHR, mismatch prompt
  voice.js       MediaRecorder, audio upload, Whisper transcription
  result.js      extraction result display, review flow, correction form
```

All shared state lives on `frappe_intelligence.widget` (accessed via `this`). No cross-module imports.

The Vue chat island (`chat_island.js`) mounts `ChatPanel.vue` inside `#fi-panel-body` and suppresses the vanilla JS realtime handler while the panel is open — restoring it on unmount.

To rebuild after JS changes:
```bash
source ~/.nvm/nvm.sh && bench build --app frappe_intelligence
```
