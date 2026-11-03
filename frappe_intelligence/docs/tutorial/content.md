# Chapters and topics

All content is in `public/js/tutorial/content.js`, with every string in `__()` (Arabic in `locale/ar.po`).

**A new feature adds its topic here**, in the chapter where a user would look for it, and updates the topic when the feature changes; its demo video scene goes in `demos.js` and is recorded again ([videos.md](videos.md)).

## Chapters

| Group | Chapters |
|---|---|
| Using the assistant (`use`) | Get started, Work faster, Let it do the work, Make it yours |
| Setting it up (`setup`) | Connect, Teach, Automate, Improve |

A chapter is numbered by its place in `CHAPTERS`; one with no visible topic is left out.

## Topic fields

| Field | Meaning |
|---|---|
| `key` | The route segment, `/desk/intelligence-tutorial/<key>`; lowercase letters, digits and hyphens (the endpoint refuses others) |
| `chapter`, `minutes`, `title`, `text` | Where it sits, how long it takes, its name and one line |
| `steps` | `[{ title, text, picture }]`: the step panels |
| `tips`, `related` | Good to know lines; other topics' keys |
| `tour` | Show me (below) |
| `try` | Try it now: `{ panel: true }` (the default for assistant topics), `{ route: [...] }` for `frappe.set_route`, or `{ new_doc: "<DocType>" }` |
| `doctype` / `report` | Setup topics: shown only when `frappe.model.can_read(doctype)`, or the report is in `frappe.boot.allowed_reports` |
| `status` | `(fi_assistant) => null \| "hidden" \| { tag, tone }`, from the boot data (`boot.py`): hide the topic, or show a tag such as **Off** (tone `off`) |

`assistant_topic()` and `setup_topic()` set the group (and the default `try`).

## Show me

`tour: [{ target, step }]` reuses step `<step>`'s title and text; `[{ target, title, text }]` gives its own. `{ target: "try_it" }` alone points at Try it now with a standard text.

A target names an element in `TARGETS` (`targets.js`): `launcher`, `panel`, `resizer`, `composer`, `send`, `context`, `mode`, `attach`, `microphone`, `history`, `new_chat`, `try_it`, `dock_workflows`, `dock_documents`, `dock_setup`, `analytics`. A new target goes there, found by class, by `item-name`, or by its `aria-label` through the same `__()` string the element uses, so it works in every language. A target missing from the screen (the dock on a phone) is skipped.

## Pictures

A topic with a demo video ([videos.md](videos.md)) shows the video instead of its pictures. `picture` names a drawing in `components/StepPicture.vue`, built from six frames: `dock`; the panel (`panel`, `resize`, `composer`, `answer`, `context`, `attach`, `microphone`, `review`, `workflows`, `workflow-bar`, `mode`, `proposal`, `history`, `rating`); a form (`settings`, `filled`, `field`, `popover`, `undo`); `list`; `builder`; `chart`. The `is-ring` class marks the element the step is about. Drawings use Frappe's theme variables, so they follow dark mode and right to left.

## Checking a topic

Open it, read every step against the real screen, press **Show me** and walk to the end, and press **Try it now**. For a setup topic, check it is hidden for a user without access.
