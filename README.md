# Frappe Intelligence

A scoped AI workflow agent for Frappe. Not a general chatbot — it guides users through ordered business workflows, enforces topic scope before spending any LLM tokens, and works identically on desk, portal, and WhatsApp.

**Three modes in one widget:**
- **Ask** — free-form chat with RAG, tool use, and streaming
- **Agent** — multi-step guided workflows with scope enforcement
- **Document** — async OCR + LLM extraction pipeline with confidence review

## Quick Install

```bash
bench get-app frappe_intelligence
bench --site <site> install-app frappe_intelligence
sudo apt install -y libgl1 libglib2.0-0 ffmpeg   # self-hosted only
bench --site <site> migrate
bench build --app frappe_intelligence
```

Then open **Frappe desk → Intelligence → AI Settings** to configure the AI provider.

## Bench Commands

| Command | What it does |
|---------|--------------|
| `bench fi-setup-ollama` | Install Ollama binary, start service, pull default model |
| `bench fi-setup-ollama --model <model>` | Pull a specific model |
| `bench fi-setup-ollama --skip-install` | Skip binary install, just pull the model |
| `bench fi-check-deps` | Print status of all Python packages, ffmpeg, Ollama |

## Documentation

| Document | What it covers |
|----------|---------------|
| [architecture/](frappe_intelligence/docs/architecture/README.md) | Target structure, conventions, restructuring status |
| [ARCHITECTURE.md](frappe_intelligence/docs/ARCHITECTURE.md) | System layers, data flows, DocType map |
| [providers/](frappe_intelligence/docs/providers/README.md) | AI providers: interface, settings, adding one |
| [agent/](frappe_intelligence/docs/agent/README.md) | Desk chat agent: loop, tools, conversations, security |
| [panel/](frappe_intelligence/docs/panel/README.md) | The docked assistant panel on the desk |
| [workflows/](frappe_intelligence/docs/workflows/README.md) | Guided workflows: panel, turns, steps, the filled record |
| [documents/](frappe_intelligence/docs/documents/README.md) | Files the assistant reads, and reviewing what it read |
| [writer/](frappe_intelligence/docs/writer/README.md) | Write with AI: long text fields written in place |
| [CONFIGURATION.md](frappe_intelligence/docs/CONFIGURATION.md) | AI Settings: providers, chat, WhatsApp, widget |
| [WORKFLOWS.md](frappe_intelligence/docs/WORKFLOWS.md) | Building workflows: steps, scope, knowledge packs, post-processors |
| [DOCUMENT_PIPELINE.md](frappe_intelligence/docs/DOCUMENT_PIPELINE.md) | Document templates, extraction rules, training |
| [INTEGRATION.md](frappe_intelligence/docs/INTEGRATION.md) | Adding the app to another Frappe app |
| [API_REFERENCE.md](frappe_intelligence/docs/API_REFERENCE.md) | All whitelisted endpoints |
| [WIDGET_GUIDE.md](frappe_intelligence/docs/WIDGET_GUIDE.md) | Widget user guide |
| [DEPLOYMENT.md](frappe_intelligence/docs/DEPLOYMENT.md) | Self-hosted and Frappe Cloud setup |

## Requirements

- Frappe v15 / v16, Python 3.10+
- One of: Ollama server (local), or an OpenAI, Anthropic or Gemini API key (cloud)

## License

MIT
