# Sheets (`api.sheets`)

## `download_sheet`

POST only. Returns a sheet the assistant compiled as a file (`Content-Disposition: attachment`), built again from the rows stored with the conversation. See [../panel/sheets.md](../panel/sheets.md).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `conversation` | str | ✓ | The AI Conversation; the user must be able to read it |
| `call_id` | str | ✓ | The `export_sheet` call that made the sheet |
| `file_format` | str | ✗ | `Excel` (default) or `CSV` |

Checks, in order: the assistant's roles (`ensure_assistant_access`), read permission on the conversation, then the Export right on every DocType the conversation read before the call (`agent/sheets.py: sheet_file`). A refusal comes back as Frappe's `PermissionError`, which the card shows. Each download is logged in Access Log as an Export.
