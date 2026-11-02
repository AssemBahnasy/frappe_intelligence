# Code

## Layout

The app follows the layout of ERPNext, HRMS and CRM:

| Kind of code | Where | Reference |
|---|---|---|
| Whitelisted endpoints | `api/`, one file per concern; they only check access and inputs, then delegate | CRM `crm/api/`, HRMS `hrms/api/` |
| External services | One package or module per provider behind a shared base and registry (`providers/`) | CRM `crm/integrations/<provider>/` |
| Business logic | Plain modules in the feature's package (`agent/`, `workflows/`, `documents/`, `writer/`) | |
| Record logic | The DocType controller | |
| Small shared helpers | `utils/` | |
| Tests | `tests/` for cross-cutting tests, beside the DocType for DocType tests | |

The full map of packages is in [../overview/code-map.md](../overview/code-map.md).

## Principles

- **Separation of concerns.** An endpoint never holds business logic; a feature package never talks to an AI service directly (only `providers/` does).
- **DRY: one source per fact.** Each tool, provider, setting and rule is declared once and read everywhere else. Prefer data-driven rules to repeated code.
- **Reuse Frappe.** Use Frappe's own APIs (its MCP data tools, `rate_limit`, `frappe.enqueue`, realtime, desk components) before writing an equivalent.
- **Permissions come from Frappe.** Every endpoint checks access on the server; data is read the way REST API v2 allows ([../agent/security.md](../agent/security.md)).
- **Few comments.** Short docstrings that say why; no comment that restates the code.

## Python

- Tabs, double quotes, line length 110 (`[tool.ruff]` in `pyproject.toml`).
- Text sent to a model stays in English; text shown to a user goes through `_()`.
- Data files (fixtures, seeds) live in the app's `data/` folder as JSON, one file per DocType; the Python only reads them.
- A DocType JSON's `modified` is bumped when it changes (never to a future date), or migrate skips it.

## Form scripts

Written the way ERPNext and Frappe core write them:

- every handler and helper is a method inside `frappe.ui.form.on("DocType", {...})`; a field event calls `frm.trigger("...")`; helpers are called as `frm.events.helper(frm, ...)`;
- per-form state lives on `frm`; no module-level functions, caches or mutable state;
- server calls through `frappe.call`, `frm.call` or `frappe.db.get_value(...).then`;
- `__()` on every user-facing string; tabs, double quotes.

Desk pages (`frappe.pages[...]`) may keep module-level helpers and classes, as Frappe's own pages do.
