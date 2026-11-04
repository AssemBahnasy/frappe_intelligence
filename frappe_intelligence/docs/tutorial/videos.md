# Demo videos

A topic can have a short video of the feature on the real desk: a cursor moves and clicks, the page zooms in on what matters, and text types itself. They are recorded from scenes, never by hand, so after a UI change one command records them again.

```bash
bench --site <dev site> fi-record-tutorial                      # every scene, English and Arabic
bench --site <dev site> fi-record-tutorial --topic ask --lang ar
```

It runs only on a site with `developer_mode`, needs Node, Google Chrome (`FI_CHROME` can point at another browser), `ffmpeg`, and the app's dev dependency `playwright-core` (installed with the app's node packages, `bench setup requirements --node`), and writes:

| Output | What |
|---|---|
| `public/tutorial/<lang>/<topic>.mp4` | 1600×900 H.264 at 30 fps, no sound (about 0.9 MB for 20 seconds) |
| `public/js/tutorial/videos.json` | `{topic: {lang: {duration, steps, version}}}`: the length, the second each step starts, and a hash of the file |

## The player (`components/TopicVideo.vue`)

Above the steps of a topic that has a video (mockup board G): it plays muted on a loop, or waits for Play when the user prefers reduced motion. Its bar has pause, a timeline with a dot where each step starts (a range input, so the keyboard and right to left work), the time, and full screen. The step on screen is lit up below with a **Playing** tag, and clicking a step plays from where it starts.

`videos.js` picks the recording in the user's language (`frappe.boot.lang`), else English, and adds the file's hash to its URL so a new recording is fetched again. The file is fetched once and played from memory: a server that does not answer range requests, like the development server, cannot be sought in otherwise.

## Sample data

Videos are recorded on a site with fictional records only (erpnext.local, company Awesome Company), never one holding real data: everything on screen ships in the app.

```bash
bench --site <dev site> fi-tutorial-sample-data
```

creates what `tutorial/sample_data.json` lists, in the default company:

| Key | Records |
|---|---|
| `customers`, `suppliers`, `items`, `sales_invoices` | ERPNext records; invoice dates are counted back from the day it runs, so some are overdue |
| `documents` | The app's own records, whole: knowledge pack, document templates, requirements, post processor, processing logs, training pairs, workflows. `_key` finds one that exists; without it, the DocType's name field does |
| `workflow_sessions` | Per workflow, how many conversations are Completed, Active and Abandoned, and their length: the numbers Session Analytics shows. They belong to whoever runs the command, so they show in that user's History |

Running it again adds nothing. A scene that needs more records adds them there.

## Scenes (`public/js/tutorial/demos.js`)

One entry per topic key: a function (it may be async) returning the `route` to start on and the `scene`, a list of actions played in order. Optional keys:

| Key | For |
|---|---|
| `boot` | Values put into `frappe.boot.fi_assistant` before the panel opens, to show what this site has off (`agent_mode`, `voice`, `workflows`) |
| `conversations` | The History menu: `[{ name, title, modified, turns: [{ question, answer }] }]` |
| `workflow` | What starting a workflow opens: `{ state, question }`, `state` as `workflows/desk.py progress` returns it |

Scripted answers are built from the site's records with `frappe.db`, so they match the list behind the panel. Texts go through `__()` and the scene is built in the recording's language, so the Arabic video types Arabic.

| Action | Does |
|---|---|
| `{ step: n }` | Marks where step `n` of the topic starts (videos.json) |
| `{ click: target }` | Moves the cursor to the target and clicks it |
| `{ hover: target }` | Moves the cursor there |
| `{ zoom: target, scale }` | Zooms until the target is in the middle (default 1.5); `{ zoom: null }` zooms out |
| `{ type: text }` | Types into what has focus |
| `{ reply: { steps, text, proposals, actions, workflow, report } }` | The assistant answers: each step label runs, then the text is written. `proposals`: changes to approve or a document's values to check (`preview` as the cards read it); `actions`: browser actions (`assistant/actions.js`); `workflow`: the workflow's next state; `report: true`: the text after the changes were decided |
| `{ attach: "<file name>" }` | Attaches a file through Attach a file (its upload is answered by the recorder) |
| `{ job: value }` | A background job finishes with `value`: the text of a recording, or what Write with AI wrote |
| `{ go: "<route>" }` | Opens another desk page (`frappe.set_route`), e.g. `permission-manager/AI Conversation` |
| `{ press: keys, label }` | Presses keys (Playwright names, e.g. `Control+.`) and shows `label` as a key badge |
| `{ drag: target, by }` | Drags the target `by` pixels along the line: negative towards its start, in either direction |
| `{ select: target, value }` | Sets a select field without the browser's own list, which is not recorded |
| `{ wait: ms }` | Holds |

A target is one Show me uses (`targets.js`; content.md lists them), or a desk element named directly (`find_target`):

| Target | Finds |
|---|---|
| `{ sidebar: "<label>" }` | A sidebar item (translated by the finder, as Frappe names items after their translated label) |
| `{ field: "<fieldname>" }`, `{ check: "<fieldname>" }`, `{ tab: "<fieldname>" }` | A form field, its checkbox, a form tab |
| `{ row: "<text>" }` | The title link of the list row that contains the text; its other columns are filter links |
| `{ label: __("…") }`, `{ input: __("…") }`, `{ button: __("…") }` | An element by its aria-label, an input by its `<label>`, a button by its text |
| `{ menu: __("…") }` | A row of an open Frappe menu, by its label |
| `{ css: "<selector>", text }` | A page's own parts (the Workflow Builder's step cards), optionally containing `text` |

Record names and values are data and stay untranslated; match a row on a value that is the same in every language (a key, not a DocType's label). A target above or below the screen is scrolled to first; one missing from the screen stops the recording and saves a screenshot of what was there.

## How it records

- `recorder.py` creates a temporary user with every desk role, signs it in, and runs `recorder.cjs` once per language. The user, its sessions and everything it logged are removed afterwards, even when a scene fails (retried while the server finishes the closed browser's last request). `videos.json` is written once, at the end, with every video that was finished, even after a failure.
- Every topic starts in a fresh browser, so what one scene leaves (an open panel, a draft) is not where the next begins. A scene may change a form, but never saves it.
- `recorder.cjs` drives Chrome through Playwright at 1280×720 (×1.5) and records the screen with Chrome's screencast. Chrome sends a frame only when the screen changes; `ffmpeg` gets one frame per 1/30 s, each the latest received, so the video's length and the step times match exactly. It loads `fi_tutorial_demos.bundle.js`, which only the recorder uses: the scenes and `stage.js` (the cursor, the click ripple, and a zoom that scales the page itself so text stays sharp).
- With `bench watch` running, writing `videos.json` rebuilds the tutorial bundle, and a developer-mode desk reloads after every build (`desk.js` `setup_build_events`). The recorder's browser gets an empty `build_events.bundle.js`, so a rebuild never reloads the page being recorded or shows its toast in a video.
- What would reach a model or write a conversation (the chat, workflow, voice, Write with AI and job endpoints, and `upload_file`) is answered inside the browser; the app's other endpoints, such as the Workflow Builder's list, go to the server, and scripted answers and job results arrive through the page's own realtime handlers (`fi_assistant`, `fi_job`), so a recording never reaches a model or writes to the database. The fake server keeps the conversation as the real one would: its turns, the workflow's state, and the decisions on proposals; a change is reported once none is left waiting.
- Voice input records from Chrome's fake microphone; the site counts as a secure origin in the recorder's browser only.
- `fi_tutorial_demos.bundle.js` may be missing while `bench watch` rebuilds; the recorder reloads until it is there.
