# Behaviour

## Where the button shows

Beside the label of every **Small Text**, **Text**, **Long Text**, **Text Editor** and **Markdown Editor** field of a form, for users allowed to use the assistant.

| Field | Button |
|---|---|
| Read-only by definition | None |
| Read-only for now (submitted, `read_only_depends_on`, no write permission) | Hidden while it stays read-only (stylesheet: Frappe hides the field's input) |
| In a child table row, a dialog or a web form | None |

## Writing

```
[✨] → popover: "What should this field say?"   ┌──────────────────────────────┐
                                                │ Short intro: clinic chain…   │
                                                └──────────────────────────────┘
                                                Ctrl Enter to write    [Write]
  → toast "Writing Customer Details…" (spinner)
  → the field is filled, ringed in violet for a moment
  → toast "Field updated  [Undo]" for 10 seconds
```

- **Ctrl+Enter** (⌘+Enter on a Mac) or **Write** sends; **Escape** or a click outside closes the popover.
- The popover remembers the last description per DocType and field while the page is open, so writing again starts from it.
- The field's current text goes with the request, so "make it more formal" rewrites what is there.
- Text Editor fields get the text as HTML (Markdown from the model through `frappe.markdown`); Markdown Editor fields get Markdown; the others plain text.
- **Undo** puts back the text from before. Nothing was saved either way.
- If the user opened another record, or changed the field themselves, before the text arrived, the text is not put anywhere and the toast says so: their own typing is never overwritten.
- Errors (AI unreachable, no text) show in a red toast; a refused request (permission, turned off) shows Frappe's message.

The button, popover and toast are Frappe's own components (`frappe.ui.Popover`, `frappe.ui.toast`) with v16 tokens, so dark mode and right-to-left need nothing extra.
