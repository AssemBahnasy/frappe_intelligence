# Exporting and printing a report

When the user asks for a report as a file, a PDF or on paper, the agent calls `export_report` (`agent/tools/reports.py`) and a card appears under the answer (`components/ExportCard.vue`, `exports.js`). It implements the approved mockup "Report download card", boards 1 to 7. A document (an invoice) is printed from Frappe's print view instead: `print_document` ([../agent/tools.md](../agent/tools.md), board 8).

```
export_report (server)                     the card (browser)
  Report exists, Query or Script report      filters, row count
  can_export / Print right on ref_doctype    Download ──► frappe.desk.query_report.export_query
  runs it once: rows, prepared or not        Print, PDF ──► the report page's own menu items
                                             Open report ──► the report, with the same filters
```

Everything is Frappe's own code: the file is the one the report page's **Export** makes, and **Print** and **PDF** open the report with the card's filters, then its own Print or PDF settings (`query_report.js: get_menu_items`). Each runs the report again, so it gives the figures as of that moment; nothing is saved on the site.

## Rules

| Rule | Enforced by |
|---|---|
| Download needs **Export** on the report's DocType (System Manager always may) | `export_report` (`frappe.permissions.can_export`), and again by `export_query` |
| Print and PDF need **Print** on it, as the report page's menu does (`frappe.model.can_print`) | `export_report` (`frappe.has_permission(..., "print")`) |
| With neither right there is no card; the agent says which is missing | `export_report` |
| Running the report needs **Report** on it | `frappe.desk.query_report.run` |
| Only Query and Script reports (Report Builder reports export from their list view) | `export_report` (`EXPORT_TYPES`) |
| Excel or CSV; Excel unless the user asked for CSV | `export_report` (`EXPORT_FORMATS`) |
| Each download is logged in Access Log as an Export, like the report page's button; Print and PDF log themselves there | `exports.js` (`make_access_log`); `query_report.js` |

## What the card offers

| `delivery` | When | The card |
|---|---|---|
| `download` | Export right, up to 10,000 rows (`EMAIL_ROWS`) | Format, **Download**; then "Downloaded at …" and **Download again** |
| `email` | Export right, more rows than that | **Email it to me**: Frappe's background export emails the user a link (`export_in_background`) |
| `print` | Print right without Export | No format or Download; the agent says the report cannot be exported |
| `open` | A prepared report | Only **Open report**: Frappe exports and prints a prepared report only from the copy prepared on its page |

**Print** and **PDF** show whenever `can_print` is set (any `delivery` but `open`). They wait for the report's new run to finish drawing (`loaded`, up to 30 seconds); a report with no rows shows a message instead, as Frappe hides its own Print then.

The format switch changes the file without asking the agent again. A refusal from the server (for example the Export right taken away since) shows in red on the card. Frappe answers "No data to export" with a page instead of a file; the card shows it as an error.

The card is a browser action (`export_report`), stored with the tool's result, so it is still there when the conversation is opened again. Cards stored before Print existed have no `can_print` and show no Print or PDF.

## Filters on the card

The filters the agent used, labelled from their field names (`report_date` → "Report Date") and translated where Frappe has the label, as are text values such as Select options; dates in the user's format. **Open report** sets them as route options on `query-report/<name>`.
