# Workflows in the assistant panel

Approved boards: 2a (where a workflow starts) and 3b (a workflow in progress).

## Starting

| Where | What |
|---|---|
| Empty panel, **Guided workflows** | Up to 3 workflows, each with its number of steps |
| Mode menu → **Start a guided workflow** | Every workflow, as a submenu |

Both list the workflows that are **Active**, **Allow Desk** and have at least one step (`boot.fi_assistant.workflows`). Choosing one calls `start_workflow`: a new conversation (mode `Workflow`, titled after the workflow) with the first step's question already asked, without AI.

## In progress (board 3b)

```
┌ ⑂ Register a new client     Step 2 of 2 · Tax Details  [Exit] ┐
│ ████████████ ▒▒▒▒▒▒▒▒▒▒▒▒                                      │  done · current · to do
│ ✓ Al Waha Clinics  ✓ Dr. Sami Al Harbi  ┆Customer Group┆        │  answers · still needed
└────────────────────────────────────────────────────────────────┘
  …the assistant's question
  [Government] [Non Profit] [Commercial] …                          quick replies
  ┌ Type your answer…                                     📎  ↑ ┐
  Saved after every answer. You can leave and come back.
```

| Part | Source (`workflows/desk.progress`) |
|---|---|
| Step label | The step key, readable (`tax_details` → Tax Details) |
| Progress | Steps by order; finished ones full, the current one lighter |
| Chips | Every answer so far (hover: its label); dashed chips for what the current step still needs |
| Quick replies | For the first field still needed, when its Target DocType field is a Select or a Link with at most 6 options. Links offer only records the user can read, never a tree's groups or disabled records |
| Off-topic · answered without AI | Under a redirect (message `off_topic`) |

The mode button is hidden: a workflow has no Ask or Agent mode. Files can still be attached; their text is read with the answer.

## Leaving and coming back

| Action | Result |
|---|---|
| **Exit** | `exit_workflow`: status Paused, the panel starts a new chat |
| History | Lists workflows with the chats; opening one shows the bar again |
| Answering a Paused workflow | It becomes Active and continues from the same step |
| Reload | The open conversation is restored, bar included |
| Last step done | Status Completed; the bar says "All N steps done"; follow-up questions are still answered within the workflow's mandate |

After the last step for a Target DocType, a new form for it opens filled with the answers ([steps.md](steps.md#the-record)).
