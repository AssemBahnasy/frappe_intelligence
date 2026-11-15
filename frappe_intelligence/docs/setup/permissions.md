# Permissions: who may use the assistant and Agent mode

Two roles, given on the User form (Roles & Permissions) or through a Role Profile. Checked on the server (`utils/access.py`) by every endpoint that reaches a model; hiding the panel and menus (`boot.py`) is only cosmetic.

| Role | Opens |
|---|---|
| **Intelligence User** | The assistant in Ask mode, Write with AI, voice input, guided workflows on the desk, the Apps screen tile |
| **Intelligence Agent** | All of the above, and Agent mode: changes the user confirms ([../agent/approvals.md](../agent/approvals.md)) |

Nobody has either role until it is given, except Administrator, which is given both on a new install and by an updated site's patch (`install.give_administrator_the_roles`), as ERPNext's `after_install` ticks every role for Administrator (`add_all_roles_to`). Frappe's setup wizard also gives its first user every role that exists by then (`create_or_update_user`). Frappe gives Administrator every role (`frappe.permissions.get_roles`), but here it follows the roles ticked on its own User form (`user_roles`), so unticking them takes the assistant away. Both are named in AI Conversation's permissions, so Frappe creates them on migrate (`make_module_and_roles`, `frappe/core/doctype/doctype/doctype.py`). Website and portal users never get the desk assistant; they use `api/portal.py`.

## The assistant (`can_use_assistant`)

A desk user (Frappe's automatic **Desk User** role) with either role.

## Agent mode (`agent_mode_refusal`)

Open when both hold:

1. **AI Settings → Allow Agent Mode** is on: the site-wide switch.
2. The user has the **Intelligence Agent** role. System Manager does not bring it.

Checked when the panel boots (the mode menu shows Agent, or why it is closed), when a message is sent in Agent mode (`api/chat.py`), and when a change card is built and when it runs (`agent/tools/changes.py`). The user's own permissions still bound every change, and Excluded DocTypes are never changed.

## AI Conversation permissions

| Role | Rights |
|---|---|
| Intelligence User, Intelligence Agent | create, read, write, delete, own conversations only |
| System Manager | everything |

## Sites from before the roles (`patches/v1_0/intelligence_user_role.py`)

Access used to be **AI Settings → Allowed Roles** (empty meant every desk user). The patch gives Intelligence User to every enabled desk user the old rule let in, and Administrator both roles; it removes the table and its child DocType, AI Widget Role, and drops its database table. Nobody else is given Intelligence Agent: an administrator gives it to the people who should have Agent mode.
