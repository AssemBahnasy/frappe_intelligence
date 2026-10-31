# Behaviour

## Header

The assistant's name, then **New chat**, **History** and **Close**. History is Frappe's own menu (`frappe.ui.Dropdown`) listing the user's recent desk conversations with their age; the open one is marked.

## New chat

A greeting with the user's first name and up to two groups of starter questions picked by role (`agent/suggestions.py`); clicking one sends it.

## Sending

- **Enter** sends, **Shift+Enter** adds a line; the box grows up to about seven lines.
- The chip above the box names the page the user is on ("Customer list", "Sales Invoice · ACC-…") and is sent as context. **×** leaves it out for this page; it comes back on the next page.
- The mode menu offers **Ask** and **Agent** (disabled with "Turned off in AI Settings" unless Agent mode is allowed). The chip turns violet in Agent mode.

## While the answer is written

| State | Shown |
|---|---|
| Before the first event | "Thinking…" with a spinner |
| A tool runs | Live list of steps: spinner while running, check when done, × when failed, square when stopped |
| Text arrives | The answer grows in place; the list follows unless the user scrolled up |

**Send** becomes **Stop**. A stopped answer keeps what was written and shows "Stopped."

## The answer

- Markdown from `frappe.markdown` (sanitised by Frappe).
- Steps fold into one line, e.g. "Reading Customer list · Counting Customer · 2 steps"; clicking opens the list.
- Tables are sortable by any column and show five rows a page with "1–5 of 7".
- Links to desk records and reports open in the desk without reloading.
- Charts from `show_chart` are drawn with `frappe.utils.make_chart`, which uses the theme's palette.
- Errors show in a red notice.
- Under the answer: **Copy as Markdown**, **thumbs up / down** (stored on the message, `rate_reply`), and when it was asked.

Browser actions from the agent (open a page, open a form, start a new document) run when the answer finishes.

## Changes in Agent mode (board 2c)

A proposed change shows as a card: what will happen, the values with field labels, a note ("Saved as Draft. You submit it." or "Nothing is saved until you confirm."), **Reject** and **Confirm**. While a card waits, the box reads "Reply, or ask for a change to the proposal…"; sending a message instead rejects the card.

After a decision the card becomes one line: a spinner while it runs, then a check with a link to the created document ("You confirmed"), × with the error, or "You rejected". The assistant's report continues under it.

## Width and theme

Drag the inner edge to resize (360 px up to 60 % of the window); double-click it to reset. The width is kept per browser. Phones show the panel full screen.

Colours, spacing and radii are Frappe v16 design tokens (`--surface-*`, `--ink-*`, `--outline-*`), so dark mode needs no extra code. Layout uses logical properties (`inset-inline-start`, `padding-inline`, `border-inline-start`) so it mirrors in right-to-left languages.
