# Code map

```
frappe_intelligence/
├── api/            whitelisted endpoints, one file per concern       → ../api/
├── providers/      AI services behind one interface                   → ../providers/
├── agent/          agent loop, prompts, tools, background runs       → ../agent/
├── workflows/      guided workflows: steps, topic gate, turns        → ../workflows/
├── documents/      reading files, templates, review, pipeline, voice → ../documents/
├── writer/         Write with AI                                      → ../writer/
├── tutorial/       which tutorial topics a user has done              → ../tutorial/
├── channels/       WhatsApp bridge                                    → ../workflows/turn.md
├── utils/          small shared helpers (below)
├── intelligence/   the Frappe module: DocTypes, report, page, sidebars, workspace
├── dock/           the app's dock                                     → ../navigation/
├── public/         panel, Write with AI, Workflow Builder, tutorial, icons, logo
├── locale/         translations (gettext)                             → ../guidelines/translations.md
├── patches/        data patches run once on migrate
├── tests/          tests over fakes                                   → ../guidelines/testing.md
└── docs/           these docs
```

## Top-level modules

| File | Job |
|---|---|
| `hooks.py` | Apps screen tile, bundles, icons, boot, WhatsApp doc event, daily task, log clearing |
| `boot.py` | `fi_assistant` in the desk boot: who may use the assistant, Agent mode, Write with AI field types |
| `install.py` | `after_install`: seeds document requirements (none by default) |
| `tasks.py` | Daily: idle workflow conversations become Abandoned |
| `commands.py` | `bench fi-setup-ollama`, `bench fi-check-deps` |

## utils/

| File | Job |
|---|---|
| `access.py` | Who may use the assistant and Agent mode (the two roles); the per-user rate limit on endpoints that reach a model |
| `background.py` | Short background jobs one browser waits for (Write with AI, voice) |
| `language.py` | The reply language; replies written without AI translated into it |
| `optional.py` | The optional OCR and voice packages |
| `fields.py` | Matching field names the AI or an administrator wrote to a DocType's real fields |
| `file_utils.py` | File URL checks and path-traversal prevention |
| `callables.py` | Callables administrators name in settings (post-processors, completion checks), from installed apps only |
| `seed_manager.py`, `requirement_seeder.py` | Seeding document templates from a JSON bundle, and document requirements |
