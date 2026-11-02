# Arabic and right to left

## Right to left (board 3c)

The panel's layout uses logical properties (`inset-inline-start`, `padding-inline`, `border-inline-start`), so it mirrors when the desk is in Arabic: docked on the left, the resize edge on its inner side, the user's questions on the left.

| Part | How |
|---|---|
| Messages, questions, chips, quick replies | `dir="auto"`: each follows its own text |
| Numbers, dates and codes in an Arabic answer | `assistant/bidi.js` puts each left-to-right run in a `<bdi>` once the answer is complete, so "ACC-SINV-2026-00017" or "86,400.00" keeps its order; Latin words next to each other stay in one run |
| Number columns in tables | Aligned to the end with tabular figures (`assistant/tables.js`) |
| Write with AI, workflow bar | Frappe's popover and toast, and logical properties |

## The reply language

The reply language follows **AI Settings → Response Language** or the user's message (`utils/language.py`). Replies written without AI, such as a workflow's redirect and closing summary, use the same language: `language.replying_to(text)` translates them into it instead of the desk language.

## Translations

Arabic ships in `locale/ar.po`; how strings are added and translated: [../guidelines/translations.md](../guidelines/translations.md).
