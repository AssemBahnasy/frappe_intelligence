# Deployment

## What Is Always Automatic

| What | How |
|------|-----|
| Python packages (`pypdf`, `requests`, `openai`, `anthropic`, `google-genai`) | `pyproject.toml`: bench installs them on `get-app` |
| APT packages (`libgl1`, `libglib2.0-0`, `ffmpeg`) | `pyproject.toml [deploy.dependencies.apt]`: Frappe Cloud installs them; only the optional packages below use them |
| Assistant in the dock and Write with AI on forms | `app_include_js` in hooks.py: no template changes needed |
| Daily session expiry | `scheduler_events`: requires bench worker (see below) |

## Optional Packages

Two features need large packages, so they are not installed by default:

| Extra | Package | Feature without it |
|---|---|---|
| `ocr` | `easyocr` (brings torch, several GB) | Photos and scanned PDF pages cannot be read; PDFs with embedded text still are. The assistant says the package is missing. |
| `voice` | `faster-whisper` | No microphone in the assistant panel |

```bash
bench pip install -e apps/frappe_intelligence[ocr,voice]   # or only one of them
sudo apt install -y libgl1 libglib2.0-0 ffmpeg            # their system libraries
bench restart
```

`bench fi-check-deps` shows which are installed. On Frappe Cloud, only the base packages are installed.

## Self-Hosted

```bash
bench get-app frappe_intelligence
bench --site <site> install-app frappe_intelligence
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
  ✓ pypdf                PDF text extraction
  ✗ easyocr              Photos and scanned PDFs (optional: the ocr extra)  ← missing
  ✓ faster_whisper       Voice input (optional: the voice extra)
  ✓ openai               OpenAI and Ollama providers
  ✓ anthropic            Claude provider
  ✓ google.genai         Gemini provider
  ✓ requests             HTTP client (Ollama model checks)

System tools:
  ✓ ffmpeg               Audio decoding for voice input (optional)

Ollama:
  ✓  Ollama running — models: qwen2.5:7b
```

### Background Workers

Assistant answers, Write with AI, voice input, the document pipeline, WhatsApp and post-processors all run in RQ workers. Ensure workers are running:

```bash
bench worker --queue long &   # assistant answers, Write with AI, voice, document extraction
bench worker --queue default  # WhatsApp + post-processors
```

The daily scheduler task (`expire_old_sessions`) runs via `bench schedule`.

## Frappe Cloud

Ollama **cannot** be installed on Frappe Cloud (requires root + persistent daemon). Use Claude instead.

1. Get an API key at console.anthropic.com
2. **AI Settings → Provider = Claude → paste key → Save → Test Connection**

The base Python and APT packages are installed automatically during Frappe Cloud deployment; the optional OCR and voice packages are not.

### Ollama on External VPS + Frappe Cloud

1. Provision any Ubuntu VPS
2. `curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen2.5:7b`
3. Expose port 11434 from Frappe Cloud IP (or use a VPN)
4. **AI Settings → Provider = Ollama → Ollama Base URL = `http://<vps-ip>:11434`**

## Provider Comparison

| | Self-Hosted | Frappe Cloud |
|--|-------------|--------------|
| Python packages | Automatic (OCR and voice: optional extras) | Automatic (without OCR and voice) |
| APT packages | `sudo apt install` | Automatic |
| Ollama | `bench fi-setup-ollama` | Not supported (external VPS option available) |
| OpenAI / Claude / Gemini | API key only | API key only |
| Recommended | Ollama (local) or a cloud provider | A cloud provider |
| Automatic fallback | ✓ cloud provider → Ollama | ✓ if external Ollama configured |

## Upgrading

```bash
bench get-app frappe_intelligence  # pulls latest
bench --site <site> migrate
bench build --app frappe_intelligence
```

Patches in `patches.txt` run once each on migrate.
