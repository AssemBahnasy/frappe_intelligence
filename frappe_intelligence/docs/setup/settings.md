# AI Settings

One Single DocType, **Intelligence → AI Settings**, read through `frappe.get_cached_doc` (a save takes effect at once).

## Model

One provider serves the whole site: **Ollama**, **OpenAI**, **Claude** or **Gemini**, with its key and model, a shared timeout, and an optional fallback to Ollama. **Test Connection** checks it after saving. Every field: [../providers/settings.md](../providers/settings.md).

## Chat

| Field | Default | Effect |
|---|---|---|
| System Prompt | empty | Added to the assistant's and workflows' instructions, e.g. the company's tone or rules |
| Response Language | empty | Languages the assistant replies in; empty means the language of each message ([../panel/language.md](../panel/language.md)) |
| Voice Transcription Language | empty | Language code for Whisper (`ar`, `en`); empty means detect it |
| Confidence Threshold | 0.6 | A document reading below it is marked "Review needed"; an AI Workflow can override it |
| Scope Similarity Threshold | 0.05 | Word-overlap score below which a workflow answer counts as off topic ([../workflows/turn.md](../workflows/turn.md#the-topic-gate)) |
| Extraction Mode | Batch with Fallback | How fields are pulled from a document with the AI ([../documents/templates.md](../documents/templates.md#extraction-mode)) |
| Keep Model Loaded | off | Ollama only: keep the model in memory between requests |

Response Language rows:

| Rows | Replies in |
|---|---|
| None | The language of each message |
| One | Always that language |
| Several | The message's language when listed, else the first row's |

## WhatsApp

Shown when the `frappe_whatsapp` app is installed.

| Field | Default | Effect |
|---|---|---|
| Enable AI on WhatsApp | off | Master switch |
| WhatsApp Account | | The business number that answers |
| AI Workflow for WhatsApp | | The workflow incoming messages go through |
| Max Reply Length (chars) | 1000 | Longer replies are split at word boundaries |
| WhatsApp System Prompt | empty | Used in place of the Chat tab's System Prompt for WhatsApp replies, e.g. for short messages without tables; empty means the general one |

Messages are answered only within Meta's 24-hour window after the user's last message.

## Assistant

| Field | Default | Effect |
|---|---|---|
| Assistant Name | empty | The name in the panel header ("Assistant" when empty) |
| Allow Agent Mode | off | The site-wide switch for Agent mode: changes the user confirms ([../agent/approvals.md](../agent/approvals.md)). Only users with the **Intelligence Agent** role can use it ([permissions.md](permissions.md)) |
| Excluded DocTypes | | DocTypes Agent mode never changes |
| Write with AI in Forms | on | The sparkles button beside long text fields ([../writer/README.md](../writer/README.md)) |

## site_config.json

Whisper (voice input) is configured per site, not in AI Settings:

```json
{"whisper_model_size": "medium", "whisper_device": "cpu", "whisper_compute_type": "int8"}
```

These are the defaults. The model loads on the first recording and stays in the worker's memory.
