# Building workflows

An **AI Workflow** is built in **Intelligence → Workflow Builder** (System Manager), which saves the workflow, its steps and its knowledge packs in one go (`api/builder.py`). The records can also be edited directly.

## AI Workflow

| Field | Purpose |
|---|---|
| Workflow Key | Slug, also the record's name (`service_request`) |
| Title | Shown in the panel and its progress bar |
| Is Active | Inactive workflows cannot be started or continued |
| Allow Desk / Allow Portal / Allow WhatsApp | The channels it runs on |
| Scope Description | The mandate: given to the model, and used by the topic gate |
| Out Of Scope Reply | Sent to an off-topic message without AI (default "That's outside this workflow.") |
| Excluded Keywords | One term per line; a message containing one always passes the topic gate |
| Confidence Threshold | Overrides AI Settings for documents read in this workflow (0 = use AI Settings) |
| Completion Message | Sent after the last step without AI; empty means a summary of the answers |
| Steps | The steps, one row each ([steps.md](steps.md)) |
| Knowledge Packs | The packs its replies may draw on ([knowledge-packs.md](knowledge-packs.md)) |

Step keys must be unique within a workflow; a duplicate is refused on save.

## Statuses

| Status | Meaning |
|---|---|
| Active | In progress |
| Paused | The user pressed **Exit** in the panel; answering again continues |
| Completed | Every step done |
| Abandoned | Idle for 7 days, or the workflow changed under it |

On the desk a workflow is a conversation of its own, reopened from History ([desk.md](desk.md)). Portal and WhatsApp conversations are found by channel, the channel's own id and workflow, so a user picks up their Active or Paused one.

## WhatsApp Flows

A step's **WhatsApp Flow** sends an interactive WhatsApp form instead of a question; the submitted answers are collected into the step. Needs Allow WhatsApp and the WhatsApp settings ([../setup/settings.md](../setup/settings.md#whatsapp)).
