# Install

Requires Frappe v16 (built and tested on v16.54: the dock, sidebars and MCP tools it uses are recent v16 features) and Python 3.14.

## Self-hosted

```bash
bench get-app frappe_intelligence
bench --site <site> install-app frappe_intelligence
bench --site <site> migrate
bench build --app frappe_intelligence
```

Then choose a provider in **AI Settings** ([settings.md](settings.md)). The assistant, its dock and Write with AI need no template changes: they come from `hooks.py`.

## What installs itself

| What | How |
|---|---|
| Python packages (`pypdf`, `requests`, `openai`, `anthropic`, `google-genai`) | `pyproject.toml`; bench installs them with the app |
| APT packages (`libgl1`, `libglib2.0-0`, `ffmpeg`) | `[deploy.dependencies.apt]`; Frappe Cloud installs them; only the optional packages use them |
| Daily expiry of idle workflow conversations | `scheduler_events`; needs the scheduler |

## Optional packages

| Extra | Package | Without it |
|---|---|---|
| `ocr` | `easyocr` (brings torch, several GB) | Photos and scanned PDF pages cannot be read; PDFs with embedded text still are. The assistant says the package is missing |
| `voice` | `faster-whisper` | No microphone in the panel |

```bash
bench pip install -e apps/frappe_intelligence[ocr,voice]   # or only one of them
sudo apt install -y libgl1 libglib2.0-0 ffmpeg
bench restart
```

`bench fi-check-deps` shows what is installed. On Frappe Cloud only the base packages are installed.

## Ollama (local model)

```bash
bench fi-setup-ollama                          # installs Ollama and pulls qwen2.5:7b
bench fi-setup-ollama --model <model>          # another model
bench fi-setup-ollama --skip-install           # Ollama already installed: only pull
```

A 7B model needs several GB of free memory next to the bench. Ollama cannot run on Frappe Cloud; there, use a cloud provider, or Ollama on a separate server reachable from the site (**AI Settings → Ollama Base URL**).

## Workers

Answers, Write with AI, voice input and document extraction run on the `long` queue; WhatsApp and post-processors on `default`. `bench start` (or supervisor in production) runs the workers and the scheduler.

Restart the workers after updating the app: they keep the old code until restarted.

## Upgrading

```bash
bench update --pull --apps frappe_intelligence    # or git pull in apps/frappe_intelligence
bench --site <site> migrate
bench build --app frappe_intelligence
bench restart
```

Patches in `patches.txt` run once each on migrate.
