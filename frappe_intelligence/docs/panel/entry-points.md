# Entry points

| Where | What |
|---|---|
| Dock | A sparkles button after Search and Notifications, made with the dock's own `make_utility()` so it looks and behaves like them |
| Sidebar | A matching row in the standard items band, shown only while the dock does not own the utilities (the same rule Frappe applies to Search and Notifications) |
| Keyboard | **Ctrl+.** toggles the panel, also while typing. Frappe's key map names the period key `>`, so it is registered as `ctrl+>` and listed that way in Frappe's shortcut help |

The launcher (`fi_launcher.bundle.js`, about 2 KB) loads on every desk page. The panel's own bundle loads on first use.

The panel remembers whether it was open and which conversation it showed, per browser, and restores both after a reload.

## Who sees it

`boot_session` (`boot.py`) adds `frappe.boot.fi_assistant` only for users who may use the assistant (`utils/access.can_use_assistant`: a desk user with the **Intelligence User** or **Intelligence Agent** role, [../setup/permissions.md](../setup/permissions.md)); `agent_mode` there is per user. Without it the launcher adds nothing. The server checks access again on every request ([../agent/security.md](../agent/security.md)).

`frappe.boot.fi_assistant` also carries the assistant's name (**AI Settings → Assistant Name**, default "Assistant") and the user's starter questions (`agent/suggestions.py`).
