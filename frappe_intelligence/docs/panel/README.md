# Assistant panel

The assistant lives in a panel docked to the right of the desk (left in right-to-left languages). It takes its width from the page instead of covering it, stays open across pages, and follows answers live. It implements the approved mockups, boards 1, 2a and 2b.

| Concern | Doc |
|---|---|
| Opening it: dock, sidebar, shortcut, who sees it | [entry-points.md](entry-points.md) |
| What the panel shows and does | [behaviour.md](behaviour.md) |
| Code structure and how it loads | [structure.md](structure.md) |

Answers come from the agent ([../agent/README.md](../agent/README.md)) and stream through the `fi_assistant` events ([../agent/live-replies.md](../agent/live-replies.md)).

## Not in the panel yet

| Feature | Arrives in |
|---|---|
| Agent mode (shown disabled in the mode menu) | Step 5 |
| Attach a document | Step 6 |
| Guided workflows in the mode menu | Step 7 |
| Voice input, Arabic translations of new strings, right-to-left review | Step 9 |

The previous floating widget (`fi.bundle.js`) no longer loads on the desk. Its code stays until steps 6 and 7 bring document review and workflows into the panel, and is removed in step 9.
