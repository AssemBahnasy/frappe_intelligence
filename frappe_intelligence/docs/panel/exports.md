# Exporting a report

When the user asks for a report as a file, the agent calls `export_report` (`agent/tools/reports.py`) and a download card appears under the answer (`components/ExportCard.vue`, `exports.js`). It implements the approved mockup "Report download card", boards 1 to 4.

```
export_report (server)                    the card (browser)
  Report exists, Query or Script report     filters, row count, Excel / CSV
  can_export(ref_doctype)                   Download ──► frappe.desk.query_report.export_query
  runs it once: rows, prepared or not       Open report ──► the report, with the same filters
```

The file is Frappe's own Export, so it is the same file the report page's **Export** button makes: column widths, the total row, the user's permissions. Download runs the report again, so it gives the figures as of that moment; nothing is saved on the site.

## Rules

| Rule | Enforced by |
|---|---|
| The user needs **Export** on the report's DocType (System Manager always may), checked before any card is shown | `export_report` (`frappe.permissions.can_export`), and again by `export_query` |
| The user needs **Report** on it | `frappe.desk.query_report.run` |
| Only Query and Script reports (Report Builder reports export from their list view) | `export_report` (`EXPORT_TYPES`) |
| Excel or CSV; Excel unless the user asked for CSV | `export_report` (`EXPORT_FORMATS`) |
| Each download is logged in Access Log as an Export, like the report page's button | `exports.js` (`make_access_log`) |

## How the file reaches the user

| `delivery` | When | The card |
|---|---|---|
| `download` | Up to 10,000 rows (`EMAIL_ROWS`) | **Download**; then "Downloaded at …" and **Download again** |
| `email` | More rows than that | **Email it to me**: Frappe's background export emails the user a link (`export_in_background`) |
| `open` | A prepared report | Only **Open report**: Frappe exports a prepared report only from the copy prepared on its page |

The format switch changes the file without asking the agent again. A refusal from the server (for example the Export right taken away since) shows in red on the card. Frappe answers "No data to export" with a page instead of a file; the card shows it as an error.

The card is a browser action (`export_report`), stored with the tool's result, so it is still there when the conversation is opened again ([../agent/tools.md](../agent/tools.md)).

## Filters on the card

The filters the agent used, labelled from their field names (`report_date` → "Report Date") and translated where Frappe has the label, as are text values such as Select options; dates in the user's format. **Open report** sets them as route options on `query-report/<name>`.
