# How the page is built

The Page-host pattern of the frappe-vue skill: page controller → lazy bundle class → Vue with a Pinia store.

```
intelligence_tutorial.js        on_page_load: page chrome, mount point, "hide" → teardown
  on_page_show (every route change) → mounted? tutorial.open(topic) : load fi_tutorial.bundle.js
    → new frappe_intelligence.ui.Tutorial({ wrapper, page, topic })
        createApp + SetVueGlobals + Pinia; page head: Show me, Try it now
        Tutorial.vue → TopicNav.vue | TopicView.vue (+ TopicVideo.vue or StepPicture.vue)
```

- **Switching topics** routes to `/intelligence-tutorial/<key>`; Frappe fires `show` again and the mounted app opens the topic, keeping the search and the list's scroll. Leaving the page unmounts it. An unknown or hidden topic opens the next one up.
- **Who sees what** is decided once per mount in the store: no `frappe.boot.fi_assistant` (set by `boot.py` only for `can_use_assistant()`) shows "not available"; topics are filtered as in [content.md](content.md).
- **Layout:** the two panes sit side by side while the tutorial is wider than 640px and stack below that, measured on the tutorial itself (`container: fi-tutorial`), so an open assistant panel counts too. Stacked, the open topic comes first.
- **Fold:** whether the list is folded is kept per browser (`localStorage`, `fi_tutorial_folded`).

## Show me (`tour.js`)

Runs on Frappe's `frappe.Driver` (driver.js 0.9, the engine Form Tour uses), and only from the button: Form Tour records with `ui_tour` start by themselves on matching routes (`desk.js setup_tours`).

- Opens the assistant panel first when a target is in it, then waits a moment: driver.js would otherwise take the starting click for a click outside and close.
- Pressing Done on the last step (its `onNext`) finishes the walk; Skip, Escape or a click outside does not.
- A route change ends the walk, as Form Tour does. It listens with `frappe.router.once`: `frappe.router.off` never removes a handler (`event_emitter.js` unbinds a new wrapper).

## Done

A finished walk calls `api.tutorial.set_done` ([../api/tutorial.md](../api/tutorial.md)). `tutorial/progress.py` keeps the user's done topics as a JSON list in their user defaults (`fi_tutorial_done`): saving a default clears the user's cached boot, and the desk reads it back with `frappe.defaults.get_user_default`. The store also updates the desk's copy (`set_user_default_local`), so leaving and coming back without a reload keeps it.
