# History

The app was rebuilt in nine steps in October and November 2026, each step deleting the code it replaced. Ideas were taken from Ask ALYF (AGPL), never its code.

| Step | What it brought |
|---|---|
| 1 | `providers/` (OpenAI added) and `documents/` reading and extraction |
| 2 | `agent/` (loop, prompts, tools), the `api/` package, AI Conversation (replacing AI Agent Session), server-side access and Frappe rate limits |
| 3 | Live replies: a background job per answer, `fi_assistant` events, Stop |
| 4 | The docked assistant panel, replacing the floating widget |
| 5 | Agent mode: change tools and approval cards |
| 6 | Document review in the panel |
| 7 | Guided workflows in the panel and on every channel |
| 8 | Write with AI |
| 9 | Arabic and right to left, voice input, optional OCR and voice packages; the old widget, its endpoints and the Route Map removed |

Then: a new logo, the Apps screen tile, the dock and sidebars for Frappe v16.54 ([../navigation/README.md](../navigation/README.md)); post-processors and document requirements on workflow steps removed, as nothing read them; bundles renamed `fi_*`; the Tutorial page ([../tutorial/README.md](../tutorial/README.md)).
