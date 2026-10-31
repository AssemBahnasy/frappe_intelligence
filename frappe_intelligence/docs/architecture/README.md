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
├── writer/         Write with AI: one field's text                → docs/writer/
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
| 6 | Document review (board 3a): paperclip in the panel, files read before the model, review card, confirmed values used, training pairs and log links, `fill_form` for the open new form; `documents/templates.py` shared with the old pipeline | Done |
| 7 | `workflows/` (board 3b): workflows in the panel (start, progress bar, quick replies, Exit), steps that move forward on every channel (answers read with the AI, completion check, topic gate fixed for short answers), filled form per Target DocType; `engine/chat.py`, `workflow.py`, `scope.py` removed | Done |
| 8 | Write with AI (board 3d): sparkles button beside long text fields in every form, popover, text written in a background job, Undo; `writer/`, `api/writer.py`, AI Settings → Write with AI in Forms | Done |
| 9 | Arabic / RTL pass, `channels/`, cleanup | Pending |

Desk chat runs through `agent/`, guided workflows through `workflows/`; both use the same background runs on the desk.
