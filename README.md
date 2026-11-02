# Frappe Intelligence

An AI assistant for the Frappe and ERPNext desk, in English and Arabic. It is docked beside every page (Ctrl+.) and works with the site's own data and permissions.

- **Ask**: questions about your records and reports, answered live with tables and charts
- **Agent**: changes the assistant prepares and you confirm one by one
- **Documents**: attach a PDF or photo; check the values read from it, then fill the form
- **Guided workflows**: step-by-step data collection that stays on topic, also on the portal and WhatsApp
- **Write with AI**: long text fields written in place, with Undo
- **Voice input**: questions spoken in the panel, transcribed on your own server

## Quick Install

```bash
bench get-app frappe_intelligence
bench --site <site> install-app frappe_intelligence
bench --site <site> migrate
bench build --app frappe_intelligence
```

Then open **Frappe desk → Intelligence → AI Settings** to configure the AI provider. Reading photos and voice input need optional packages: see [setup/install.md](frappe_intelligence/docs/setup/install.md#optional-packages).

## Bench Commands

| Command | What it does |
|---------|--------------|
| `bench fi-setup-ollama` | Install Ollama binary, start service, pull default model |
| `bench fi-setup-ollama --model <model>` | Pull a specific model |
| `bench fi-setup-ollama --skip-install` | Skip binary install, just pull the model |
| `bench fi-check-deps` | Print status of all Python packages, ffmpeg, Ollama |

## Documentation

Start at [docs/README.md](frappe_intelligence/docs/README.md): what the app is, the rules for changing it ([guidelines/](frappe_intelligence/docs/guidelines/README.md)), how it fits together ([overview/](frappe_intelligence/docs/overview/README.md)), setup ([setup/](frappe_intelligence/docs/setup/README.md)), the endpoints ([api/](frappe_intelligence/docs/api/README.md)), and a folder per feature.

## Requirements

- Frappe v16, built and tested on v16.54: the dock, sidebars, desk components and MCP tools it uses are recent v16 features. Python 3.14 (`requires-python` in `pyproject.toml`)
- One of: Ollama server (local), or an OpenAI, Anthropic or Gemini API key (cloud)

## License

MIT
