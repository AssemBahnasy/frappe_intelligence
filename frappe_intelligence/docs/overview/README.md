# Overview

How the app's pieces fit together.

| Concern | Doc |
|---|---|
| Every package and its job | [code-map.md](code-map.md) |
| The DocTypes and how they relate | [doctypes.md](doctypes.md) |
| How the app got its current shape | [history.md](history.md) |

## Layers

```
 Channels       desk panel (Vue)        portal app          WhatsApp (frappe_whatsapp)
                     │                      │                       │
 Endpoints      api/chat, api/workflows  api/portal          channels/whatsapp.py
                     │                      │                       │
 Features       agent/ (Ask, Agent)  ·  workflows/  ·  documents/  ·  writer/
                     │
 Models         providers/  →  OpenAI | Claude | Gemini | Ollama
```

Endpoints check access and inputs, then hand over to a feature package. Only `providers/` talks to an AI service.

## Request flows

**Desk question** ([../agent/README.md](../agent/README.md))

```
api.chat.send_message → background job agent.runs.execute → agent.loop.run_turn
  → provider.complete(history, system prompt, tools) → tools → … until a plain answer
  → fi_assistant realtime events (text, step, done) → the panel
```

**Guided workflow** ([../workflows/turn.md](../workflows/turn.md))

```
desk:               api.workflows.start_workflow, then answers through api.chat.send_message
portal / WhatsApp:  workflows.sessions.reply
  → workflows.turn.run_turn: topic gate → answer read into the step → next step → reply
```

**Document in the panel** ([../documents/review.md](../documents/review.md)): attached files are read before the model answers; a file matching a template pauses the turn with a review card.

**Document pipeline** ([../documents/pipeline.md](../documents/pipeline.md)): `api.documents.process_document` reads and extracts a file in a background job for the portal, WhatsApp and other apps, and reports on the `ai_processing_complete` event.

**Write with AI and voice** ([../writer/server.md](../writer/server.md), [../panel/voice.md](../panel/voice.md)): a short background job (`utils/background.py`) whose result arrives on the `fi_job` event.

## State

| Where | What |
|---|---|
| AI Conversation | Every desk chat and workflow session, on every channel |
| AI Settings | Read through `frappe.get_cached_doc`, which Frappe clears on save |
| Redis | Frappe `rate_limit` counters (`rl:<endpoint>:<user>`, 60 s); WhatsApp rate limit `fi_rl_wa:{phone}` (60 s) and dedup lock `fi_wa_proc:{message_id}` (5 min); Stop flags `fi_assistant_stop:{run}`; short job results `fi_job:{user}:{job}` (10 min) |
