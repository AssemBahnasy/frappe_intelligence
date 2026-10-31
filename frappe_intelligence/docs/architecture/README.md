# Architecture

## Principles

- **Separation of concerns.** Whitelisted endpoints only check permissions and inputs, then delegate. Business logic lives in plain modules; record logic lives in DocType controllers.
- **One source per fact.** Each tool, provider and setting is declared once and read everywhere else.
- **Frappe conventions.** Layout follows ERPNext, HRMS and CRM: an `api/` package with one file per concern (CRM `crm/api/`, HRMS `hrms/api/`), one package per external integration behind a shared base (CRM `crm/integrations/<provider>/`), tests beside DocTypes plus a `tests/` package.

## Target structure

```
frappe_intelligence/
├── api/            thin whitelisted endpoints, one file per concern
├── providers/      AI services behind one interface              → docs/providers/
├── agent/          agent loop, prompts, tool registry             → docs/agent/
├── workflows/      guided workflows and the scope gate
├── documents/      file reading, transcription, extraction
├── channels/       WhatsApp bridge
├── utils/          small shared helpers
├── intelligence/   the Frappe module: DocTypes, report, page, sidebar
├── public/js/      assistant panel, field writer, workflow builder
├── tests/          cross-cutting tests
└── docs/           one folder per feature, README as index
```

## Migration status

The app moves into this structure step by step; each step deletes the code it replaces.

| Step | Area | Status |
|---|---|---|
| 1 | `providers/` (OpenAI added), `documents/reader.py`, `transcriber.py`, `heuristic.py`, `extractor.py`; `models/` removed | Done |
| 2 | `agent/` (loop, prompts, tools), `api/` package, AI Conversation (replaces AI Agent Session), server-side access, Frappe rate limits, security fixes | Done |
| 3 | Live replies: background job per run, `fi_assistant` events with run id, Stop, progress saved per step | Done |
| 4 | Assistant panel (boards 1, 2a, 2b): docked panel, dock and sidebar entries, Ctrl+., live steps, Stop, history, tables, charts, feedback; old floating widget no longer loaded | Done |
| 5 | Agent mode: change tools, approval cards, decide endpoint with row lock, savepoints, excluded DocTypes, Allow Agent Mode setting | Done |
| 6 | Document review | Pending |
| 7 | `workflows/` on the desk | Pending |
| 8 | Field writer | Pending |
| 9 | Arabic / RTL pass, `channels/`, cleanup | Pending |

Desk chat runs through `agent/`. Guided workflows still run in `engine/chat.py` (`workflow_reply`) until step 7 moves them to `workflows/`.
