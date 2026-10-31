# AI Providers

The `providers/` package is the only code that talks to an AI service. Everything else (chat, workflows, document extraction) asks it for one model turn through the same interface, whichever provider the administrator picked.

| Provider | AI Settings option | SDK | Notes |
|---|---|---|---|
| OpenAI | `OpenAI` | `openai` (Chat Completions) | Optional Base URL reaches Azure OpenAI, OpenRouter, Groq, vLLM |
| Claude | `Claude` | `anthropic` | Prompt caching; server-side refusal fallback on current models |
| Gemini | `Gemini` | `google-genai` | Tool schemas passed through unchanged |
| Ollama | `Ollama` | `openai` against Ollama's `/v1` endpoint | Local; data stays on the server |

One provider serves the whole site. The administrator chooses it; users do not pick a model.

## Files

| Concern | Doc |
|---|---|
| The interface: `Message`, `Reply`, `complete()`, errors | [interface.md](interface.md) |
| AI Settings fields and how they are read | [settings.md](settings.md) |
| Adding a fifth provider | [adding-a-provider.md](adding-a-provider.md) |

## Code map

| File | Responsibility |
|---|---|
| `providers/__init__.py` | `get_provider()` and the name → class registry |
| `providers/base.py` | Shared types, `Provider` base class, error messages, `checked()` |
| `providers/openai.py` | OpenAI and compatible servers |
| `providers/ollama.py` | Ollama: OpenAI provider pointed at `/v1`, plus model checks and keep-loaded |
| `providers/claude.py` | Anthropic SDK |
| `providers/gemini.py` | google-genai SDK |
| `providers/fallback.py` | Retry on Ollama when the main provider fails |
| `tests/test_providers.py` | Fake-SDK tests for every provider; no keys or site needed |

Run the tests from `frappe-bench/sites`:

```bash
../env/bin/python -m unittest frappe_intelligence.tests.test_providers frappe_intelligence.tests.test_extractor
```
