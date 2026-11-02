# UI

## Mockups first

Every UI decision (a new screen, widget, layout or restyle) is shown as a mockup and approved before any implementation code is written. The approved boards are referred to by number in the feature docs (for example the panel's boards 1, 2a–2c, 3a–3d).

## Vue in the desk

Bundles are named `frappe_intelligence_<feature>.bundle.js`. Only the small launcher and Write with AI (plain JS on Frappe's popover) load on every page (`app_include_js`); the panel and the Workflow Builder are Vue 3 and load with `frappe.require` when opened:

- a plain JS class mounts the Vue app (`createApp` → `SetVueGlobals` → Pinia → mount) and unmounts it on destroy;
- styling uses Frappe's CSS variables and logical properties (`inset-inline-start`, `padding-inline`), so dark mode and right to left work without extra code.

How the panel loads: [../panel/structure.md](../panel/structure.md).

## Desk components and colours

- Use Frappe's own components (`frappe.ui.Dialog`, `frappe.ui.Popover`, `frappe.ui.toast`, `frappe.utils.make_chart`) before writing new ones.
- Status colours come from the DocType's states, never from a colour map in the view.
- Charts use the theme's palette.

## Icons

Desk icons are animated two-tone symbols in one sprite, `public/icons/module-icons.svg`, in the logo's colours: [../navigation/README.md](../navigation/README.md). The Apps screen tile is the logo itself.

## Right to left

Layouts mirror in Arabic through logical properties; numbers, dates and codes inside Arabic answers keep their order: [../panel/language.md](../panel/language.md).
