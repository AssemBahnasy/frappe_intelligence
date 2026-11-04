# Frappe Intelligence docs

Start here. These docs are how anyone, person or AI agent, learns the app and the rules for changing it. Read this page, then [guidelines/](guidelines/README.md), then the folder for the feature you are working on.

## The app

An AI assistant for the Frappe and ERPNext desk, in English and Arabic, MIT licensed. It works with the site's own data and permissions:

| Feature | What it does | Docs |
|---|---|---|
| Assistant panel | Docked beside every desk page (Ctrl+.), answers live | [panel/](panel/README.md) |
| Ask and Agent modes | Reads data and reports; in Agent mode proposes changes the user confirms | [agent/](agent/README.md) |
| Documents | Reads an attached PDF, photo or text file; the user checks the values first | [documents/](documents/README.md) |
| Guided workflows | Step-by-step data collection on the desk, the portal and WhatsApp | [workflows/](workflows/README.md) |
| Write with AI | Writes a long text field in place, with Undo | [writer/](writer/README.md) |
| Tutorial | A desk page teaching every feature, with walkthroughs on the real desk | [tutorial/](tutorial/README.md) |
| Navigation | Apps screen tile, dock, sidebars, icons | [navigation/](navigation/README.md) |

Every model call goes through one provider the administrator picks (OpenAI, Claude, Gemini or a local Ollama): [providers/](providers/README.md).

Requires Frappe v16, built and tested on v16.54, and Python 3.14.

## The folders

| Folder | Read it to |
|---|---|
| [guidelines/](guidelines/README.md) | Know the rules every change follows: code, UI, translations, tests, docs |
| [overview/](overview/README.md) | See how the pieces fit: layers, request flows, code map, DocTypes, history |
| [setup/](setup/README.md) | Install, configure, permissions, integrate with another app, troubleshoot |
| [api/](api/README.md) | Call the whitelisted endpoints |
| Feature folders (table above) | Change or explain one feature |

Each folder has a README that is only an index; each file covers one concern.

## Where to start for a task

| Task | Read first |
|---|---|
| Any change | [guidelines/](guidelines/README.md) |
| A new or changed feature | its topic in [tutorial/content.md](tutorial/content.md) |
| A new tool for the assistant | [agent/tools.md](agent/tools.md), [agent/security.md](agent/security.md) |
| A new AI provider | [providers/adding-a-provider.md](providers/adding-a-provider.md) |
| Something in the panel | [guidelines/ui.md](guidelines/ui.md), [panel/structure.md](panel/structure.md) |
| A workflow behaviour | [workflows/turn.md](workflows/turn.md), [workflows/steps.md](workflows/steps.md) |
| Reading documents | [documents/review.md](documents/review.md), [documents/templates.md](documents/templates.md) |
| A new AI Settings field | [setup/settings.md](setup/settings.md) |
| A new role or permission | [setup/permissions.md](setup/permissions.md) |
| A user-facing string | [guidelines/translations.md](guidelines/translations.md) |
| A desk icon | [navigation/README.md](navigation/README.md) |
