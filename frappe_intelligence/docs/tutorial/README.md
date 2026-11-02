# Tutorial

A desk page, **Tutorial** (`/desk/intelligence-tutorial`, in the Intelligence sidebar and on the Home workspace), that teaches every feature of the app one topic at a time. It implements the approved mockups (boards 1, 3, 4, E option 3 and F).

- **Topic list:** chapters on a line of progress nodes, one chapter open at a time; closed chapters show a dot per topic; the list folds to a rail of chapter numbers.
- **Tutorial pane:** Continue where you left off, the open topic's steps with a small picture each, Good to know, Related, Previous and Next.
- **Try it now** opens the real place; **Show me** walks through the topic on the desk and marks it done.

Each user sees only what they can use: no page without assistant access, no setup topics without access to their settings, and an **Off** tag where AI Settings turned a feature off.

| Concern | Doc |
|---|---|
| Chapters and topics: the fields, adding a topic, tours, pictures | [content.md](content.md) |
| How the page is built: page host, store, Show me, Done | [structure.md](structure.md) |
| The endpoint | [../api/tutorial.md](../api/tutorial.md) |

## Code

| Piece | Responsibility |
|---|---|
| `intelligence/page/intelligence_tutorial/` | The Page record (role Desk User) and its controller: lifecycle only |
| `public/js/fi_tutorial.bundle.js` | Loaded by the page when it opens; exposes `frappe_intelligence.ui.Tutorial` |
| `public/js/tutorial/tutorial.js` | The class: mounts Vue, the page-head buttons, Try it now, Show me |
| `public/js/tutorial/content.js` | Chapters and topics |
| `public/js/tutorial/store.js` | Visible topics, done, the open topic, search, open chapter, fold |
| `public/js/tutorial/tour.js` | Show me, on `frappe.Driver` |
| `public/js/tutorial/components/` | `TopicNav.vue` (list and rail), `TopicView.vue` (tutorial pane), `StepPicture.vue` (step pictures) |
| `tutorial/progress.py`, `api/tutorial.py` | Which topics a user has done |
