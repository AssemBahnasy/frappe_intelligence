# Assistant panel

The assistant lives in a panel docked to the right of the desk (left in right-to-left languages). It takes its width from the page instead of covering it, stays open across pages, and follows answers live. It implements the approved mockups, boards 1, 2a, 2b, 2c, 3a, 3b and 3c.

| Concern | Doc |
|---|---|
| Opening it: dock, sidebar, shortcut, who sees it | [entry-points.md](entry-points.md) |
| What the panel shows and does | [behaviour.md](behaviour.md) |
| Code structure and how it loads | [structure.md](structure.md) |
| Guided workflows in the panel | [../workflows/desk.md](../workflows/desk.md) |
| Voice input | [voice.md](voice.md) |
| Arabic, right to left, translations | [language.md](language.md) |

Answers come from the agent ([../agent/README.md](../agent/README.md)) and stream through the `fi_assistant` events ([../agent/live-replies.md](../agent/live-replies.md)).
