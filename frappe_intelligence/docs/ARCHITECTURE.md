# Architecture

## System Layers

```
┌──────────────────────────────────────────────────────────────┐
│  Channels                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  Desk widget │  │ Portal (Vue/ │  │  WhatsApp incoming │ │
│  │  (JS + Vue)  │  │  React app)  │  │  (frappe_whatsapp) │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘ │
└─────────┼─────────────────┼──────────────────── ┼────────────┘
          │ api.py          │ api_portal.py        │ engine/whatsapp_handler.py
          ▼                 ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│  engine/                                                     │
│  ┌────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐  │
│  │  chat.py   │ │ workflow.py  │ │ scope.py │ │orchestr. │  │
│  │ (intent +  │ │ (session +   │ │ (pre-LLM │ │(document │  │
│  │  RAG +     │ │  step state  │ │  gate)   │ │ pipeline)│  │
│  │  tools)    │ │  machine)    │ └──────────┘ └──────────┘  │
│  └────────────┘ └──────────────┘                            │
└──────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│  models/                                                     │
│  llm_factory → ClaudeAdapter | VLMAdapter | HeuristicAdapter │
│  reader.py (OCR + PDF)   transcriber.py (Whisper)           │
└──────────────────────────────────────────────────────────────┘
```

## Key Files

| Path | Responsibility |
|------|---------------|
| `api.py` | Desk channel endpoints — rate limiting, auth, enqueue |
| `api_portal.py` | Portal channel endpoints — portal user auth guard |
| `engine/chat.py` | Intent classification, RAG retrieval, tool dispatch, history |
| `engine/workflow.py` | Session CRUD, step state machine, turn persistence |
| `engine/scope.py` | Pre-LLM gate: keyword regex + TF-IDF cosine similarity |
| `engine/orchestrator.py` | Document pipeline controller; RQ background entry-point |
| `engine/whatsapp_handler.py` | WhatsApp doc_event bridge → enqueue → route by content type |
| `models/llm_factory.py` | Select adapter + optional fallback wrapper |
| `models/claude_adapter.py` | Anthropic Claude API (prompt caching, tool use) |
| `models/vlm_adapter.py` | Ollama VLM (4 extraction strategies, keep-alive) |
| `models/heuristic_adapter.py` | Regex extractor (no LLM call) |
| `models/reader.py` | EasyOCR (images) + pypdf (digital PDFs) |
| `models/transcriber.py` | Faster-Whisper voice-to-text |
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

AI Agent Session
  └── AI Agent Turn       (child — role + content per message)

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
  → adapter.extract(raw_text, rules)
  → update log (status: Completed, extracted_data, confidence_score)
  → if confidence >= threshold: fire_post_processors()
  → frappe.publish_realtime("ai_processing_complete", result)

Browser: realtime event → _handleProcessingResult()
Fallback: poll get_log_status() every 5 s
```

### Chat / Agent (synchronous)

```
Widget → api.handle_widget_input(input_type="text", chat_mode, workflow_key)
  → _language_rule()  ← AI Response Language rows
  → classify_text_intent()
      → engine/scope.py: check_scope()  ← keyword gate + cosine similarity
        out-of-scope → return redirect_reply immediately (zero LLM tokens)
      → _retrieve_knowledge()           ← keyword score over AI Knowledge Entries
      → _doctype_schema_context()       ← field list, cached 300 s in Redis
      → _get_chat_history()             ← Redis, TTL 2 h, capped 20 turns
      → adapter.chat(prompt, tools=FRAPPE_TOOLS)
          → streaming: publish_realtime("ai_stream_chunk")
          → tool call: execute_tool() → action + action_data
  ← {reply, action, action_data}
```

### Workflow (Agent mode)

```
engine/chat.py: _classify_workflow_mode(session, text)
  → scope gate → check_scope(text, workflow_doc)
  → if no active step: completion_message or LLM summary
  → build_step_prompt(session, step)
      → injects required_fields, collected_data, knowledge_packs context
  → LLM reply → collect_step_data() → advance_step() if complete
  → append_turn() persists to AI Agent Turn child table
```

### Portal Channel

```
AIPortalClient.chat(text)
  → api_portal.portal_chat(text, customer, workflow_key)
      → _assert_portal_user(customer)           # Portal User table check
      → _enforce_portal_rate_limit(customer)    # key: fi_rl_portal:{customer}
      → classify_text_intent(channel="portal")  # same engine, no FRAPPE_TOOLS
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
  → get_or_create_session(channel="whatsapp", channel_id=phone)
  → _enforce_wa_rate_limit()   # key: fi_rl_wa:{phone}, 10/60s
  → route by content_type: text | flow | audio | image | document | button
  → text: _within_24h_window check → classify_text_intent()
  → flow: parse JSON → collect_step_data() → advance_step()
  → reply via _send_whatsapp_reply() with char-limit splitting
```

## LLM Adapter Interface

Both adapters expose the same two methods:

| Method | Used by | Returns |
|--------|---------|---------|
| `extract(raw_text, rules)` | orchestrator | `(dict, float)` — extracted fields + confidence |
| `chat(prompt, history, tools)` | chat.py | `(reply, error)` |

Ollama extraction modes (AI Settings → Extraction Mode):

| Mode | LLM calls | Best for |
|------|-----------|---------|
| Per Field | 1 per field | Weak hardware |
| Batch | 1 total | Fast hardware + strong models |
| Batch with Fallback *(default)* | 1 batch + retry on None | Recommended |
| Parallel | 1 per field, concurrent | Mid-range hardware |

## Scope Enforcement

`engine/scope.py` runs before every LLM call in workflow mode:

1. **Excluded keywords bypass** — terms in `AI Workflow.excluded_keywords` skip the keyword gate (domain-specific terms that look off-topic)
2. **Keyword gate** — regex patterns block obvious off-topic requests (jokes, weather, arithmetic)
3. **Cosine similarity** — TF-IDF cosine score of user text vs `scope_description`; below threshold → reject with `out_of_scope_reply`

Threshold: `AI Settings.scope_similarity_threshold` (default `0.05`). Per-workflow `excluded_keywords` (one per line) bypass step 2.

## Confidence & Review

`confidence_score` comes from the extraction adapter. The threshold is resolved as:

1. `AI Workflow.confidence_threshold` (if > 0) — per-workflow override
2. `AI Settings.confidence_threshold` — global setting
3. `0.6` — hard default

Below threshold → `needs_review=True` → widget shows editable review panel → post-processors held until user accepts.

## Redis Keys

| Key pattern | Purpose | TTL |
|-------------|---------|-----|
| `fi_rl:{user}` | Desk rate limit counter | 60 s |
| `fi_rl_portal:{customer}` | Portal rate limit counter | 60 s |
| `fi_rl_wa:{phone}` | WhatsApp rate limit counter | 60 s |
| `fi_wa_proc:{message_id}` | WhatsApp dedup lock | 5 min |
| `fi_schema:{doctype}` | DocType field schema cache | 300 s |
| `fi_route_map` | Route map cache | 1 h |
| `fi_chat:{session_id}` | Chat history | 2 h |
