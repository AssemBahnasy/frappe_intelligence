# Adding a provider

1. **Class** — create `providers/<name>.py` with a `Provider` subclass:
   - `name` (the AI Settings option) and `settings_prefix`;
   - `default_model`, and `default_base_url` / `requires_api_key = False` when they apply;
   - `complete()`: convert `Message`s to the SDK format, stream text through `on_text`, return `self.checked(Reply(...))`;
   - map SDK exceptions with `self.error_from(exc, ((SdkAuthError, "auth"), ...))`.
   If the service speaks the OpenAI API, subclass `OpenAIProvider` instead and override `_client()`, as `OllamaProvider` does.
2. **Registry** — add `"<Option>": "frappe_intelligence.providers.<name>.<Class>"` to `PROVIDERS` in `providers/__init__.py`.
3. **Settings** — in `ai_settings.json` add the option to `ai_provider`, and a section (`depends_on: eval:doc.ai_provider=='<Option>'`) with `<prefix>_api_key` (Password), `<prefix>_model` and, if needed, `<prefix>_base_url`.
4. **Dependency** — add the SDK to `pyproject.toml` and to `bench fi-check-deps` in `commands.py`.
5. **Tests** — add a class to `tests/test_providers.py` with a fake client: text streaming, a tool call, message conversion and one SDK error.
6. **Docs** — add a row to [README.md](README.md) and [settings.md](settings.md).
