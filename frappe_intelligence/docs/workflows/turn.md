# One workflow turn

`workflows/turn.run_turn(conversation, hooks)` answers the latest user message. The desk runs it in the background job of [../agent/live-replies.md](../agent/live-replies.md) (`runs.execute` picks it for mode `Workflow`), so replies stream and Stop works. The portal and WhatsApp call it directly through `sessions.reply`.

```
user message
  → workflow Active and allowed on the channel?           no → "This workflow is not available here."
  → Paused → Active
  → step removed since the conversation started?          yes → Abandoned, "start it again"
  → scope.is_off_topic (phrases, no AI)                   yes → redirect + the step's question   [off_topic]
  → answers.read: the step's empty fields from the answer, the question it answers and attached files (AI)
      AI unreachable                                      → the error, as for any failed answer
      nothing found and scope.is_related is false (no AI) → redirect + question                  [off_topic]
  → steps.collect; nothing missing and the completion check passes
      → steps.advance; on the desk, records.form_action (filled new form)
  → last step done                                        → Completion Message, or a list of the answers, without AI
  → otherwise the model writes the reply: thanks, then what is still needed
```

## The topic gate

| Check | Catches | Notes |
|---|---|---|
| `is_off_topic` | "tell me a joke", the weather, arithmetic… | Runs first |
| `is_related` | A message that gave no answer and shares no subject words with the mandate, the step's question and its field labels | Question words ("what", "the") are left out; skipped when the message and the mandate are in different languages, since they cannot share words |

A line of **Excluded Keywords** in the message lets it through both. No workflow mandate (Scope Description) means no gate. Threshold: **AI Settings → Scope Similarity Threshold** (default 0.05).

The redirect is the workflow's **Out Of Scope Reply** (default "That's outside this workflow."), followed by the current step's question. Replies written without AI are in the language the user writes in (AI Settings → Response Language, else the message's own language), not the desk language.

## What the model is told

| Part | Content |
|---|---|
| System | AI Settings system prompt (on WhatsApp, the WhatsApp System Prompt when set; `turn.company_prompt`); the workflow rules (one step at a time, never invent values, never say anything was saved); the mandate; the current step (`turn.instructions`); matching entries of the workflow's own knowledge packs |
| User message | The language rule as a note, then the message |
| History | Earlier messages as first sent, without the model's earlier reasoning (`provider_messages(thinking=False)`), since the system part changes every turn |

`turn.step_instructions` is also what **Workflow Builder → Preview** shows for a step.

## Reading the answer

`answers.read` sends one extraction per turn through `documents/extractor.py` (AI Settings → Extraction Mode), with one rule per field the current step still needs. Fields already answered are left out: a small model tends to copy a new answer into them too. When the completion check refused the step, every field is filled, so all of them are read again and the user's correction replaces the earlier answers. The text is the assistant's last question, the user's answer and up to 4000 characters of attached files.

The extraction runs with `strict=True`: when the AI cannot be reached, the turn ends with the error instead of reading the message as an answer that gave nothing.
