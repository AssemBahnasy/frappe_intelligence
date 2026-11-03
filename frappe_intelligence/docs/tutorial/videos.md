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
| `public/js/tutorial/videos.json` | `{topic: {lang: {duration, steps}}}`: the length, and the second each step starts |

## Sample data

Videos are recorded on a site with fictional records only (erpnext.local, company Awesome Company), never one holding real data: everything on screen ships in the app.

```bash
bench --site <dev site> fi-tutorial-sample-data
```

creates the customers, items and submitted sales invoices in `tutorial/sample_data.json`, in the default company, with dates counted back from the day it runs (some invoices overdue). Running it again adds nothing. A scene that needs more records adds them there.

## Scenes (`public/js/tutorial/demos.js`)

One entry per topic key: a function (it may be async) returning the `route` to start on and the `scene`, a list of actions played in order. Scripted answers are built from the site's records with `frappe.db`, so they match the list behind the panel. Texts go through `__()` and the scene is built in the recording's language, so the Arabic video types Arabic.

| Action | Does |
|---|---|
| `{ step: n }` | Marks where step `n` of the topic starts (videos.json) |
| `{ click: target }` | Moves the cursor to the target and clicks it |
| `{ hover: target }` | Moves the cursor there |
| `{ zoom: target, scale }` | Zooms until the target is in the middle (default 1.5); `{ zoom: null }` zooms out |
| `{ type: text }` | Types into what has focus |
| `{ reply: { steps, text } }` | The assistant answers: each step label runs, then the text is written |
| `{ wait: ms }` | Holds |

Targets are the ones Show me uses (`targets.js`; content.md lists them). A target missing from the screen stops the recording and saves a screenshot of what was there.

## How it records

- `recorder.py` creates a temporary user with every desk role, signs it in, and runs `recorder.cjs` once per language. The user, its sessions and everything it logged are removed afterwards, even when a scene fails.
- `recorder.cjs` drives Chrome through Playwright at 1280×720 (×1.5) and records the screen with Chrome's screencast. Chrome sends a frame only when the screen changes; `ffmpeg` gets one frame per 1/30 s, each the latest received, so the video's length and the step times match exactly. It loads `fi_tutorial_demos.bundle.js`, which only the recorder uses: the scenes and `stage.js` (the cursor, the click ripple, and a zoom that scales the page itself so text stays sharp).
- The assistant's endpoints are answered inside the browser and scripted answers arrive through its own realtime handler, so a recording never reaches a model or writes to the database.
