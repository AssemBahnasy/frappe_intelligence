# Tools (`agent/tools/`)

## Available in Ask mode

| Tool | Source | Does |
|---|---|---|
| `search_doctypes` | Frappe MCP | DocType names containing a query |
| `get_doctype_schema` | Frappe MCP | Fields and the user's permissions on a DocType |
| `list_documents` | Frappe MCP | Like `frappe.get_list`: filters, fields, order, paging |
| `get_document` | Frappe MCP | One document with child tables |
| `count_documents` | Frappe MCP | Like `frappe.get_count` |
| `search_reports` | `reports.py` | Reports whose name matches, that the user may run |
| `run_report` | `reports.py` | Columns and the first 50 rows; says when there are more |
| `search_knowledge` | `knowledge.py` | Matching AI Knowledge Pack entries |
| `read_document` | `documents.py` | A file's text; a template match pauses for the user to check the values ([../documents/review.md](../documents/review.md)). Called by the loop for every attached file |
| `navigate` | `desk.py` | Browser opens a `/app/…` route |
| `open_document` | `desk.py` | Browser opens a document's form |
| `new_document` | `desk.py` | Browser opens a new unsaved form with values filled in; the user saves |
| `fill_form` | `desk.py` | Browser fills values into the new form the user has open; keys are field names or labels; missing and read-only fields are left out and reported to the model; values the form's own scripts overwrite (e.g. the due date after the supplier) are put back |
| `show_chart` | `desk.py` | Chart drawn under the answer (bar, line, pie, percentage, donut) |

**Frappe MCP** tools are Frappe's own (`frappe/mcp/tools`), the same ones its built-in MCP server exposes. They run through REST API v2, so permissions, validation and argument checking are exactly those of `/api/v2/document/…`.

## Agent mode only

`create_document`, `update_document`, `delete_document`, `submit_document`, `cancel_document` (`changes.py`). Each has a `preview` that builds the approval card; it runs only after the user confirms. See [approvals.md](approvals.md).

## Declaring a tool

```python
AgentTool(
	name="run_report",
	description="…what the model reads…",
	parameters={…JSON schema…},
	run=run_report,          # takes the arguments dict, returns JSON-serialisable data
	label=_lt("Running {report_name}"),   # step label shown to the user
	modes=READ_MODES,        # which modes offer it (AGENT_ONLY for changes)
	browser_action=False,    # True: the result's "action" is performed by the browser
	preview=None,            # a change: builds the approval card; run waits for the user
	review=False,            # True: the result's "review" card pauses the turn for the user
)
```

Add it to the module's `TOOLS` list. `registry()` collects `TOOLS` from `frappe_data`, `reports`, `knowledge`, `documents`, `desk` and `changes`; add a new module there. A label can name any argument, e.g. `{file_name}`; a missing one shows as empty.

## Errors (`execute()`)

| Raised in `run` | The model receives | The user sees |
|---|---|---|
| `ToolError` | its message | nothing extra |
| `frappe.PermissionError`, `DoesNotExistError`, `ValidationError` | the message, HTML stripped | no dialog (`frappe.clear_messages()`) |
| anything else | "The tool failed unexpectedly." | nothing; the traceback goes to Error Log |

## Browser actions

Desk tools return `{"action": {...}, "status": "..."}`. The loop collects the actions in `TurnResult.actions` for the panel to perform; the stored tool result keeps them so the history can redraw charts.

| `action.type` | Fields |
|---|---|
| `set_route` | `route` |
| `open_form` | `doctype`, `name` |
| `new_doc` | `doctype`, `defaults` |
| `fill_form` | `doctype`, `values`; a new form if the user has left the one they had open |
| `chart` | `title`, `chart_type`, `labels`, `datasets[{name, values}]` |
