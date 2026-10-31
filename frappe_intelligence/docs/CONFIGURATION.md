# Configuration

All configuration lives in **Frappe desk → Intelligence → AI Settings** (Single DocType).

## Model Tab

### Providers

One provider serves the whole site: `Ollama`, `OpenAI`, `Claude` or `Gemini`, with a shared timeout and an optional Ollama fallback. Every field is described in [providers/settings.md](providers/settings.md).

**Extraction Modes** (`extraction_mode`, all providers):

| Mode | Model calls | Best for |
|------|-----------|---------|
| Per Field | 1 per field | Weak hardware or unstable models |
| Batch | 1 total | Fast hardware + strong models |
| Batch with Fallback | 1 batch + per-field retry on None | Recommended default |
| Parallel | 1 per field, concurrent | Mid-range hardware |

### Test Connection

Click **Test Connection** after saving to verify the active provider is reachable. Response:
- `ok: true` — provider is live
- `ok: false` + error message — connection failed

## Chat Tab

### System Prompt

Sets the AI persona for all chat and voice replies. If empty, a generic assistant prompt is used.

```
You are a procurement assistant for Acme Corp. Help users manage purchase
orders, supplier records, and inventory. Reply in English only.
```

In workflow mode the prompt is extended with the workflow's `scope_description`.

### Response Language Table

Controls which language(s) the AI replies in.

| Configuration | Behaviour |
|--------------|-----------|
| Empty | Auto-detect per message (recommended) |
| `ar` only | Always Arabic |
| `en` only | Always English |
| `ar` + `en` | Detects input; replies in matching language |
| Any set | Falls back to first row if detected language is not in set |

Read from the cached AI Settings document; a save takes effect immediately.

### Voice Transcription Language

ISO 639-1 code for Faster-Whisper (e.g. `ar`, `en`). Leave empty to auto-detect the spoken language.

### Extraction Behaviour

| Field | Default | Notes |
|-------|---------|-------|
| `confidence_threshold` | `0.6` | Global threshold; overridden per-workflow in AI Workflow.confidence_threshold |
| `scope_similarity_threshold` | `0.05` | TF-IDF cosine threshold for scope enforcement |

## Widget Tab

### Appearance

| Field | Default | Effect |
|-------|---------|--------|
| `widget_color` | `#6c63ff` | FAB, header, buttons, spinner (`--fi-primary` CSS var) |
| `text_color` | *(empty)* | Widget header text colour override |
| `widget_icon` | *(empty)* | Replaces default emoji with a custom image URL |
| `assistant_name` | *(empty)* | Display name shown in the widget header |

### Access Control

**Allowed Roles** child table — list Frappe roles that can see the widget.

| Configuration | Result |
|--------------|--------|
| Empty | All logged-in users see the widget |
| One or more rows | Only users holding at least one listed role see it |

Enforced on the server for every endpoint that reaches a model; the widget also hides itself for users who are not allowed.

## Navigation Tab

**Route Map** child table — controls the "Go to …" button after document classification in global mode.

| Column | Example |
|--------|---------|
| Document Type Key | `supplier_invoice` |
| Button Label | `Purchase Invoice` |
| Route | `/app/purchase-invoice/new` |

Routes must start with `/app/`.

## WhatsApp Tab

Visible only when `frappe_whatsapp` app is installed.

| Field | Notes |
|-------|-------|
| `enable_ai_on_whatsapp` | Master switch — off by default |
| `whatsapp_account` | Link to WhatsApp Account (which business number to use) |
| `whatsapp_workflow` | Link to AI Workflow applied to all incoming WhatsApp messages |
| `whatsapp_max_reply_chars` | Default 1000 — long replies are split at word boundaries |
| `whatsapp_system_prompt` | Optional system prompt override for the WhatsApp channel |

24-hour window: the engine only processes WhatsApp messages within 24 hours of the last user message (Meta's free-form messaging window). Outside this window, messages are silently ignored.

## Voice Transcription (site_config.json)

Faster-Whisper settings live in `sites/<site>/site_config.json` (not in AI Settings):

```json
{
  "whisper_model_size": "medium",
  "whisper_device": "cpu",
  "whisper_compute_type": "int8"
}
```

The model is loaded lazily on first voice request and cached in the worker process.
