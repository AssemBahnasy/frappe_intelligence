# Deployment

## What Is Always Automatic

| What | How |
|------|-----|
| Python packages (`pypdf`, `easyocr`, `faster-whisper`, `anthropic`, `requests`) | `pyproject.toml` — bench installs on `install-app` |
| APT packages (`libgl1`, `libglib2.0-0`, `ffmpeg`) | `pyproject.toml [deploy.dependencies.apt]` — Frappe Cloud installs automatically |
| Widget JS injection | `app_include_js` in hooks.py — no template changes needed |
| WhatsApp roles | `after_migrate` hook — idempotent, runs on every migrate |
| Daily session expiry | `scheduler_events` — requires bench worker (see below) |

## Self-Hosted

```bash
bench get-app frappe_intelligence
bench --site <site> install-app frappe_intelligence
sudo apt install -y libgl1 libglib2.0-0 ffmpeg
bench --site <site> migrate
bench build --app frappe_intelligence
```

### Ollama Setup (one command)

```bash
bench fi-setup-ollama                        # installs Ollama + pulls qwen2.5:7b
bench fi-setup-ollama --model llama3.2-vision:11b  # specific model
bench fi-setup-ollama --skip-install         # just pull (Ollama already installed)
```

Then open **AI Settings → Provider = Ollama → Ollama Base URL → Test Connection**.

### Verify Dependencies

```bash
bench fi-check-deps
```

Sample output:
```
Python packages:
  ✓  pypdf                PDF text extraction
  ✓  easyocr              Image OCR
  ✓  faster_whisper       Voice transcription
  ✓  anthropic            Claude provider
  ✓  requests             HTTP client

System tools:
  ✓  ffmpeg               Audio decoding

Ollama:
  ✓  Ollama running — models: qwen2.5:7b
```

### Background Workers

The document pipeline, WhatsApp handler, and post-processors all run in RQ workers. Ensure workers are running:

```bash
bench worker --queue long &   # document extraction (timeout 600 s)
bench worker --queue default  # WhatsApp + post-processors
```

The daily scheduler task (`expire_old_sessions`) runs via `bench schedule`.

## Frappe Cloud

Ollama **cannot** be installed on Frappe Cloud (requires root + persistent daemon). Use Claude instead.

1. Get an API key at console.anthropic.com
2. **AI Settings → Provider = Claude → paste key → Save → Test Connection**

All Python and APT packages are installed automatically during Frappe Cloud deployment.

### Ollama on External VPS + Frappe Cloud

1. Provision any Ubuntu VPS
2. `curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen2.5:7b`
3. Expose port 11434 from Frappe Cloud IP (or use a VPN)
4. **AI Settings → Provider = Ollama → Ollama Base URL = `http://<vps-ip>:11434`**

## Provider Comparison

| | Self-Hosted | Frappe Cloud |
|--|-------------|--------------|
| Python packages | Automatic | Automatic |
| APT packages | `sudo apt install` | Automatic |
| Ollama | `bench fi-setup-ollama` | Not supported (external VPS option available) |
| Claude | API key only | API key only |
| Recommended | Ollama (local) or Claude | Claude |
| Automatic fallback | ✓ Claude → Ollama | ✓ if external Ollama configured |

## Upgrading

```bash
bench get-app frappe_intelligence  # pulls latest
bench --site <site> migrate
bench build --app frappe_intelligence
```

`after_migrate` hooks run automatically on migrate (WhatsApp role setup, etc.).
