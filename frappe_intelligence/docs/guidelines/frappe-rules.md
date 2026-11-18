# Frappe decides

The app obeys Frappe's rules, logic and algorithms. Frappe may already decide something, such as who may read, export, print or change a record, what a child table may do, or what makes a document valid. When it does, the app asks Frappe through Frappe's own function, at run time. It never writes its own version, copies the logic or keeps a hard-coded list.

## How to apply

1. **Find the desk feature that does the same thing**, such as the Report view's Export, the form's Print button or a list's filters. Read its code in `apps/frappe`; that code is the rule.
2. **Call the function it calls** (`can_export`, `has_permission`, `is_table`, `get_parent_doctypes`, `get_list`). Never re-implement it. When Frappe applies the rule inline, not as a function, mirror it line for line and cite the file.
3. **Decide at run time, from the site.** Roles, permissions, DocTypes, fields and child tables are read when the code runs, never listed in the app. Something added later, whether a role, a DocType or one of the assistant's tools, is then covered without a code change.
4. **Never looser than Frappe, and stricter only in the open.** If the app needs a stricter rule, its feature doc says what and why. Example: a sheet does not accept Export on one's own records only.
5. **What Frappe refuses stays refused.** No `ignore_permissions` for work done for a user. The assistant never works around a refusal or asks for a role to get past one ([../agent/security.md](../agent/security.md)).
6. **Cite it.** Each rule in a feature's docs names the Frappe function it follows.

## Examples in the app

| Question | Frappe's answer | Used in |
|---|---|---|
| May the user read these records? | Frappe's MCP data tools (REST API v2), `get_list` with its field permissions | `agent/tools/frappe_data.py` |
| May the user export this DocType or report? | `frappe.permissions.can_export`, as `desk/reportview` and `desk/query_report` export | `agent/sheets.py`, `agent/tools/reports.py` |
| May the user print it? | `frappe.has_permission(doctype, "print")`, as the form's Print button | `agent/tools/desk.py: print_document` |
| Who decides for a child table? | Its parent (`permissions.has_child_permission`); parents from `linked_with.get_parent_doctypes` | `sheets.child_tables` |
| How is a report run with filters? | `frappe.desk.query_report.run` | `agent/tools/reports.py` |
| How is a file built and logged? | `make_xlsx`, `get_csv_bytes`, `provide_binary_file`, `make_access_log` | `api/sheets.py` |
