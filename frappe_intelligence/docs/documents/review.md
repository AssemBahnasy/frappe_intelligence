# Document review in the panel

The user attaches a file with the paperclip, with or without a message. The assistant reads it before answering. When it matches a template, the values read from it are shown as a card the user corrects; **their values, not the first reading, are what the assistant uses** (approved board 3a).

## Flow

```
paperclip → Frappe upload_file (private File) → chip in the box
send_message(message, attachments=[file_url, …])
  → each file checked with validate_file_access; at most 3
  → user message stored with its attachments

background run (agent/loop.py)
  → _read_attachments: one read_document call per file, before the model is asked
      documents/review.read: text → template match → field values → AI Processing Log
        no template → the model gets the text and works from it
        template    → the turn pauses with a review card
  → [Use these values] → decide_proposal(..., values={field_key: value})
      documents/review.confirm: values the model gets, training pair if edited,
      log linked to the conversation (and to the open record, with write access)
  → the model continues the request with the checked values
```

## What the assistant does next

The page the user is on decides, through the page note (`agent/prompts.page_note`):

| Page | What happens |
|---|---|
| A new, unsaved form (e.g. New Purchase Invoice) | `fill_form` puts the values into that form; nothing is saved, the user checks and saves |
| A list, e.g. Purchase Invoice | Ask mode: `new_document` opens a filled new form. Agent mode: `create_document`, with the approval card ([../agent/approvals.md](../agent/approvals.md)) |
| Anywhere else | The message says what to make, or the assistant asks |

## The card

| Part | Source |
|---|---|
| Title | Template's Document Name |
| "5 of 6 fields found" | Fields that got a value |
| "Review needed" | Confidence below **AI Settings → Confidence Threshold** (default 0.6) |
| Fields | Every extraction rule, by label, editable; a missing one is amber with "Not found — enter or leave blank" |
| **Discard** | The model is told the values were set aside |
| **Use these values** | The values as the user left them |

Sending a message instead keeps the reading for the model, marked as not confirmed, so a reply like "the total is 15,000" can correct it.

## What the model reads

```json
{"document": "invoice-gulfpack-8841.pdf", "template": "Supplier Invoice",
 "values": {"supplier": "…", "bill_no": "GP-8841", "due_date": "2026-11-30"},
 "labels": {"supplier": "Supplier", "bill_no": "Bill No", "due_date": "Due Date"},
 "edited_by_user": ["Supplier", "Due Date"],
 "note": "These are the values the user checked and corrected: use them exactly. …",
 "text": "first 6000 characters of the document"}
```

The checked values come before the text so a small model reads them first. They are keyed by the rules' field keys: naming those after the target DocType's fields (`bill_no`, `bill_date`) lets the values go straight into its form.

## Records

| Record | When |
|---|---|
| AI Processing Log | Every reading that matched a template: text, first values, confidence, `channel = desk` |
| AI Training Pair | The user changed a value: original and corrected values, linked to the log and the conversation |
| Log links | On confirm: `session` = the conversation; `linked_doctype` / `linked_docname` = the open record when the user may edit it (the record's document checklist counts these) |

Readings without a template create no log.

## Security

| Risk | Guard |
|---|---|
| Reading someone else's file | `validate_file_access` in `send_message` and again in the tool |
| Huge or many files | Frappe's upload size limit; at most 3 files a message; the model gets the first 6000 characters |
| Values injected from the browser | Only the card's own field keys are used, each cut to 1000 characters |
| Filling a form with unknown fields | `fill_form` leaves out field names the DocType does not have and tells the model; the browser skips them too |

Post-processors (AI Post Processor) are not run from the panel; they belong to the workflow and WhatsApp channels. The old widget's `confirm_extraction` now passes them the values the user corrected.
