# Architecture

> The app is being restructured; see [architecture/README.md](architecture/README.md) for the target layout and migration status.

## System Layers

```
┌──────────────────────────────────────────────────────────────┐
│  Channels                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Desk panel   │  │ Portal (Vue/ │  │  WhatsApp incoming │ │
│  │ (Vue)        │  │  React app)  │  │  (frappe_whatsapp) │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘ │
└─────────┼─────────────────┼──────────────────── ┼────────────┘
          │ api/chat.py     │ api/portal.py       │ engine/whatsapp_handler.py
          │ api/workflows.py│                     │
          ▼                 ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│  agent/          loop · tools · runs (background, streaming) │
│  workflows/      steps · scope · answers · turn · records    │
│  engine/         orchestrator (document pipeline) · WhatsApp │
└──────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│  providers/  get_provider → OpenAI | Claude | Gemini | Ollama│
│  documents/  reader · transcriber · heuristic · extractor    │
│  reader.py (OCR + PDF)   transcriber.py (Whisper)           │
└──────────────────────────────────────────────────────────────┘
```

## Key Files

| Path | Responsibility |
|------|---------------|
| `api/` | Whitelisted endpoints, one module per concern; see [API_REFERENCE.md](API_REFERENCE.md) |
| `agent/` | Agent loop, prompts and tools for desk chat; see [agent/README.md](agent/README.md) |
| `workflows/` | Guided workflows on every channel; see [workflows/README.md](workflows/README.md) |
| `engine/orchestrator.py` | Document pipeline controller; RQ background entry-point |
| `engine/whatsapp_handler.py` | WhatsApp doc_event bridge → enqueue → route by content type |
| `providers/__init__.py` | `get_provider()`: the provider chosen in AI Settings, with optional Ollama fallback |
| `providers/{openai,claude,gemini,ollama}.py` | One class per AI service behind a shared interface |
| `documents/extractor.py` | AI field extraction (4 strategies) over any provider |
| `documents/heuristic.py` | Regex extractor (no AI call) |
| `documents/reader.py` | EasyOCR (images) + pypdf (digital PDFs) |
| `documents/transcriber.py` | Faster-Whisper voice-to-text |
| `utils/file_utils.py` | File URL validation + path-traversal prevention |
| `utils/seed_manager.py` | JSON bundle → AI Document Template seeder |
| `tasks.py` | Scheduled tasks (daily: expire stale sessions) |

## DocType Map

```
AI Settings (Single)
  ├── AI Response Language  (child — allowed chat reply languages)
  ├── AI Route Map          (child — document_type_key → Frappe route)
  └── AI Widget Role        (child — roles permitted to see the widget)

AI Workflow
  ├── AI Workflow Step           (child — ordered steps)
  ├── AI Workflow Knowledge Pack (child — assigned RAG packs)
  └── AI Workflow Post Processor (child — step_key → post-processor)

AI Document Template
  └── AI Extraction Rule  (child — field_key, regex, LLM hint)

AI Knowledge Pack
  └── AI Knowledge Entry  (child — topic + content snippets)

AI Conversation           (desk chats and workflow sessions, every channel)
  └── AI Conversation Message (child — user, assistant, tool turns)

AI Processing Log  ←── AI Training Pair (links log + session)
AI Document Requirement   (target DocType → required document_type_key)
AI Post Processor         (callback_method registry)
```

## Data Flows

### Document Extraction (async)

```
Widget → api.process_document
  → validate_file_access()
  → create AI Processing Log (status: Pending)
  → frappe.enqueue(queue="long", timeout=600)
  ← {"status": "queued", "log_name": "..."}   # immediate HTTP return

RQ worker → process_document_background
  → reader.py: OCR / PDF text
  → classify by keyword scoring (or direct template key)
  → documents.extractor.extract(raw_text, rules)
  → update log (status: Completed, extracted_data, confidence_score)
  → if confidence >= threshold: fire_post_processors()
  → frappe.publish_realtime("ai_processing_complete", result)

Browser: realtime event → _handleProcessingResult()
Fallback: poll get_log_status() every 5 s
```

### Desk chat

```
api.chat.send_message(message, conversation, context)   ← returns {conversation, run_id}
  → utils.access.ensure_assistant_access()
  → background job agent.runs.execute → agent.loop.run_turn()     (handle_widget_input runs it synchronously)
      → provider.complete(history, system prompt, Ask-mode tools)
      → agent.tools.execute(call) … repeat until a plain-text answer (max 8 steps)
      → AI Conversation rows saved
  → fi_assistant realtime events: text, step, done
```

See [agent/loop.md](agent/loop.md) and [agent/live-replies.md](agent/live-replies.md).

### Workflow

```
desk: api.workflows.start_workflow → first question (no AI); answers → api.chat.send_message
      → agent.runs.execute → workflows.turn.run_turn
portal / WhatsApp: workflows.sessions.reply → workflows.turn.run_turn
  → workflow Active and allowed on the channel
  → topic gate (no AI) → read the answer into the step's missing fields (AI)
  → step complete → completion check → next step; desk: filled form for the Target DocType
  → reply: the model (thanks + next question); after the last step, the Completion Message or a summary, without AI
```

See [workflows/turn.md](workflows/turn.md).

### Portal Channel

```
AIPortalClient.chat(text)
  → api.portal.portal_chat(text, customer, workflow_key)
      → _assert_portal_user(customer)           # Portal User table check
      → _enforce_portal_rate_limit(customer)    # key: fi_rl_portal:{customer}
      → workflows.sessions.reply(text, "Portal", user, workflow_key)
  ← {reply, action, action_data}
```

### WhatsApp Channel

```
WhatsApp Message.after_insert
  → whatsapp_handler.on_whatsapp_message()
      → feature gate: _is_whatsapp_enabled()
      → dedup: Redis fi_wa_proc:{message_id} (5-min TTL)
      → frappe.enqueue("process_whatsapp_message_job", queue="default")

RQ worker → process_whatsapp_message_job
  → workflows.sessions.session("WhatsApp", phone, workflow_key)
  → _enforce_wa_rate_limit()   # key: fi_rl_wa:{phone}, 10/60s
  → route by content_type: text | flow | audio | image | document | button
  → text: _within_24h_window check → workflows.sessions.reply()
  → flow: parse JSON → steps.collect() → steps.advance() → next question
  → reply via _send_whatsapp_reply() with char-limit splitting
```

## AI Providers

Every model call goes through `providers/`; see [providers/README.md](providers/README.md). Document extraction strategies are in `documents/extractor.py`; see [DOCUMENT_PIPELINE.md](DOCUMENT_PIPELINE.md) and [documents/README.md](documents/README.md).

## Scope Enforcement

Workflows only: see [workflows/turn.md](workflows/turn.md#the-topic-gate).

## Confidence & Review

`confidence_score` comes from the extractor. The threshold is resolved as:

1. `AI Workflow.confidence_threshold` (if > 0) — per-workflow override
2. `AI Settings.confidence_threshold` — global setting
3. `0.6` — hard default

Below threshold → `needs_review=True` → widget shows editable review panel → post-processors held until user accepts.

## Redis Keys

| Key pattern | Purpose | TTL |
|-------------|---------|-----|
| `rl:<endpoint>:<user>` | Frappe `rate_limit` counters (desk and portal endpoints) | 60 s |
| `fi_rl_wa:{phone}` | WhatsApp rate limit counter | 60 s |
| `fi_wa_proc:{message_id}` | WhatsApp dedup lock | 5 min |

AI Settings (route map, allowed roles, response languages) is read through `frappe.get_cached_doc`, which Frappe clears on save. Conversations are stored in AI Conversation, not Redis.
