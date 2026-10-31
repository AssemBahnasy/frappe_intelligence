# Arabic, right to left, translations

## Right to left (board 3c)

The panel's layout uses logical properties (`inset-inline-start`, `padding-inline`, `border-inline-start`), so it mirrors when the desk is in Arabic: docked on the left, the resize edge on its inner side, the user's questions on the left.

| Part | How |
|---|---|
| Messages, questions, chips, quick replies | `dir="auto"`: each follows its own text |
| Numbers, dates and codes in an Arabic answer | `assistant/bidi.js` puts each left-to-right run in a `<bdi>` once the answer is complete, so "ACC-SINV-2026-00017" or "86,400.00" keeps its order; Latin words next to each other stay in one run |
| Number columns in tables | Aligned to the end with tabular figures (`assistant/tables.js`) |
| Write with AI, workflow bar | Frappe's popover and toast, and logical properties |

The reply language follows **AI Settings → Response Language** or the user's message (`utils/language.py`).

## Translations

Arabic ships in `locale/ar.po` (gettext, like Frappe, ERPNext and HRMS); `locale/main.pot` lists every string. `bench build` compiles them.

After changing user-facing strings:

```bash
bench generate-pot-file --app frappe_intelligence
bench update-po-files --app frappe_intelligence --locale ar
# translate the new empty msgstr entries in locale/ar.po
bench compile-po-to-mo --app frappe_intelligence
```

Strings are wrapped in `__()` in JavaScript and Vue, `_()` / `_lt()` in Python; DocType labels and descriptions are picked up from the JSON. Text sent to the model (prompts, rules) stays in English.
