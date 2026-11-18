# Sheets the assistant compiles

When the user wants as a file a table no report gives (sales against target per sales person), the agent compiles it from the records it read and hands it over as Excel or CSV (`agent/sheets.py`, `agent/tools/sheets.py`, `components/SheetCard.vue`). It implements the approved mockup "Report download card", boards 9 to 11. For an existing report the agent uses `export_report` instead ([exports.md](exports.md)).

```
check_export_rights     the Export right on every DocType it plans to read; refused → stop, read nothing
read the records        list_documents, get_document, run_report ... (the user's permissions)
answer                  the table, shown in the answer
export_sheet            Export on every DocType the conversation read → the card
Download                api/sheets.py: the same check again → Frappe's make_xlsx / get_csv_bytes
```

## Rules

| Rule | Enforced by |
|---|---|
| Before reading anything, the agent checks the Export right on every DocType it plans to use, and stops if one is refused | the system prompt (`agent/prompts.py`), `check_export_rights` |
| A sheet needs the Export right (`frappe.permissions.can_export`) on every DocType the conversation read before it, taken from the stored tool calls, not from what the model says | `sheets.read_doctypes`, `sheets.ensure_exportable`, in `export_sheet` and again at each download |
| A report read counts as its reference DocType | `sheets.read_doctypes` |
| A sheet is built only after records were read in the conversation | `export_sheet` |
| 1 to 50 columns, 1 to 5,000 rows, one value per column | `sheets.validate_sheet` |
| Only the conversation's owner (or System Manager) can download it | `api/sheets.download_sheet` (AI Conversation permissions) |
| Each download is logged in Access Log as an Export, with the sheet's title | `api/sheets.download_sheet` |
| Text that looks like a formula stays text | Frappe's `make_xlsx` and `get_csv_bytes` |

## Where the sheet lives

Nowhere on the site as a file. Its rows are the `export_sheet` call's arguments, stored with the conversation; each download builds the file again from them (`sheets.sheet_file`). Deleting the conversation removes the sheet. The card (`action.type` `export_sheet`) carries the conversation, the call id, the title, the columns, the row count and **Built from**, never the rows.

## The card

**Built from**, the columns and the format; a note that the assistant compiled it, not a report, with the panel's warning to check important figures; **Download**, then "Downloaded at …" and **Download again**. The frame is shared with the report card (`components/FileCard.vue`).

The figures come from the model, so the same rows are shown as a table in the answer: the user sees what the file holds before taking it.
