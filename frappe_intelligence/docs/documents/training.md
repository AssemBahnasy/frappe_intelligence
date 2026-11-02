# Processing logs and training pairs

## AI Processing Log

Every document reading, from the panel or the pipeline:

| Field | Content |
|---|---|
| Processing Status | `Pending` → `Processing` → `Completed` or `Failed` |
| Confidence Score | 0 to 1 |
| Extracted Data | The values read, by field key (JSON) |
| Raw Text | The full text read from the file |
| Session | The AI Conversation it was read in, if any |
| Linked DocType / Linked Docname | The record the values went to |

Readable by the user who had it read and by System Managers.

## AI Training Pair

Created when the user changes a value before using it (the panel's review card, or `api.documents.submit_correction`):

| Field | Content |
|---|---|
| Document Template, Processing Log, Session | Where the reading came from |
| Original Extraction | The values as read |
| Corrected Extraction | The values as the user left them |
| Correction Source | Who corrected them |
| Applied | Ticked once someone has acted on it |

Training pairs are not fed back to the model. They show where a template reads badly: fix its regex patterns, AI hints or detection keywords, then tick **Applied**.
