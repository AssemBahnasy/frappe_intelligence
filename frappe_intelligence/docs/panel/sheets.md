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

Who may take a sheet is decided by Frappe's own export rules, through Frappe's functions at run time ([../guidelines/frappe-rules.md](../guidelines/frappe-rules.md)). The app adds no permission rule of its own.

| Rule | Frappe's rule it follows | Enforced by |
|---|---|---|
| A sheet needs the Export right on every DocType the conversation read before it | Exports check `frappe.permissions.can_export` (`desk/reportview._export_query`, `desk/query_report.export_query`) | `sheets.ensure_exportable`, in `export_sheet` and again at each download |
| What was read comes from the stored tool calls: each tool declares the DocType it returns (`AgentTool.reads`), not what the model says | | `sheets.read_doctypes` |
| A report read counts as its reference DocType | The report export checks Export on `ref_doctype` | `reports.report_doctype` |
| Fields taken through a link (`project.project_name`) or a child table (`sales_team.sales_person`) come with the DocType listed | The Report view exports such fields under the listed DocType's right; the query engine leaves out the ones the user may not read (`database/query.py: apply_field_permissions`) | Frappe's `get_list` |
| A child table (Sales Team) is never checked by itself; the agent is told the documents it sits in | A child table has no rights of its own: Frappe checks its parent (`permissions.has_child_permission`); parents from `desk/form/linked_with.get_parent_doctypes` | `sheets.child_tables`, `check_export_rights` |
| Export on one's own records only is not enough | The report export allows it neither (`can_export` without `is_owner`); a compiled row has no single owner | `sheets.export_rights` |
| Before reading anything, the agent checks the Export rights and stops if one is refused | | the system prompt (`agent/prompts.py`), `check_export_rights` |
| A sheet is built only after records were read in the conversation | | `export_sheet` |
| 1 to 50 columns, 1 to 5,000 rows, one value per column | | `sheets.validate_sheet` |
| Only the conversation's owner (or System Manager) can download it | AI Conversation permissions | `api/sheets.download_sheet` |
| Each download is logged in Access Log as an Export, with the sheet's title | `make_access_log`, as the desk's exports do | `api/sheets.download_sheet` |
| Text that looks like a formula stays text | `make_xlsx`, `get_csv_bytes` | Frappe |

## Where the sheet lives

Nowhere on the site as a file. Its rows are the `export_sheet` call's arguments, stored with the conversation; each download builds the file again from them (`sheets.sheet_file`). Deleting the conversation removes the sheet. The card (`action.type` `export_sheet`) carries the conversation, the call id, the title, the columns, the row count and **Built from**, never the rows.

## The card

**Built from**, the columns and the format; a note that the assistant compiled it, not a report, with the panel's warning to check important figures; **Download**, then "Downloaded at …" and **Download again**. The frame is shared with the report card (`components/FileCard.vue`).

The figures come from the model, so the same rows are shown as a table in the answer: the user sees what the file holds before taking it.
