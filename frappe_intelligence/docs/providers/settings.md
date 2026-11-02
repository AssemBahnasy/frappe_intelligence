# Provider settings (AI Settings → Model)

| Field | Applies to | Notes |
|---|---|---|
| `ai_provider` | all | `Ollama`, `OpenAI`, `Claude` or `Gemini`. One provider for the whole site |
| `request_timeout` | all | Seconds to wait for the provider (default 60) |
| `enable_ollama_fallback` | OpenAI, Claude, Gemini | Answer from Ollama when the main provider fails before streaming anything |
| `openai_api_key`, `openai_model` | OpenAI | |
| `openai_base_url` | OpenAI | Empty = OpenAI. Any OpenAI-compatible URL otherwise (Azure OpenAI, OpenRouter, Groq, vLLM) |
| `claude_api_key`, `claude_model` | Claude | Default model `claude-opus-5-5` |
| `gemini_api_key`, `gemini_model` | Gemini | |
| `ollama_base_url`, `ollama_model` | Ollama | Defaults `http://localhost:11434`, `qwen2.5:7b` |
| `keep_model_loaded` | Ollama | Preloads the model once with `keep_alive: -1` so it stays in memory |
| `extraction_mode` | all | On the Chat tab: how document fields are extracted with the AI ([../documents/templates.md](../documents/templates.md#extraction-mode)) |

## How they are read

`Provider.from_settings()` reads `<prefix>_api_key`, `<prefix>_model` and `<prefix>_base_url` for the provider's `settings_prefix`, falling back to the same keys in `site_config.json`, then to the class defaults. Settings come from `frappe.get_cached_doc("AI Settings")`, so a save takes effect on the next request.

## Claude refusal fallback

On `claude-fable-5-1`, `claude-fable-5`, `claude-opus-5-5`, `claude-opus-5` and `claude-sonnet-5-5`, requests carry `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`). If Claude's safety classifiers decline, the API retries on Anthropic's recommended model for that refusal category inside the same call. Other Claude models are called without it.

## Test Connection

The button on AI Settings calls `api.settings.test_connection`, which runs `provider.test_connection()`:

- cloud providers send a one-word prompt;
- Ollama checks that the configured model is pulled and names the `ollama pull` command if not.
