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
| `navigate` | `desk.py` | Browser opens a `/app/…` route |
| `open_document` | `desk.py` | Browser opens a document's form |
| `new_document` | `desk.py` | Browser opens a new unsaved form with values filled in; the user saves |
| `show_chart` | `desk.py` | Chart drawn under the answer (bar, line, pie, percentage, donut) |

**Frappe MCP** tools are Frappe's own (`frappe/mcp/tools`), the same ones its built-in MCP server exposes. They run through REST API v2, so permissions, validation and argument checking are exactly those of `/api/v2/document/…`. Write tools from the same set (`create_document`, `update_document`, `delete_document`) come with Agent mode in step 5, behind the user's approval.

## Declaring a tool

```python
AgentTool(
	name="run_report",
	description="…what the model reads…",
	parameters={…JSON schema…},
	run=run_report,          # takes the arguments dict, returns JSON-serialisable data
	label=_lt("Running {report_name}"),   # step label shown to the user
	modes=READ_MODES,        # which modes offer it
	browser_action=False,    # True: the result's "action" is performed by the browser
)
```

Add it to the module's `TOOLS` list. `registry()` collects `TOOLS` from `frappe_data`, `reports`, `knowledge` and `desk`; add a new module there.

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
| `chart` | `title`, `chart_type`, `labels`, `datasets[{name, values}]` |
