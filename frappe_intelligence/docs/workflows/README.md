# Guided workflows

An **AI Workflow** takes the user through its steps one at a time, collecting the answers each step asks for. It runs the same way in the desk panel, on the portal and on WhatsApp.

| Concern | Doc |
|---|---|
| Starting, answering and leaving a workflow in the panel (boards 2a, 3b) | [desk.md](desk.md) |
| One turn: topic gate, reading the answer, moving on, the reply | [turn.md](turn.md) |
| Steps, required fields, completion check, the record a workflow fills | [steps.md](steps.md) |
| Building workflows (Workflow Builder), knowledge packs, post-processors | [../WORKFLOWS.md](../WORKFLOWS.md) |

## Code

| Piece | Responsibility |
|---|---|
| `workflows/steps.py` | The step machine: current step, collected answers, completion check, next step |
| `workflows/scope.py` | Topic gate without AI: off-topic phrases, word overlap with the mandate |
| `workflows/answers.py` | The user's answer read into the step's fields, with the AI provider |
| `workflows/turn.py` | One turn on any channel; the opening question; what the model is told |
| `workflows/records.py` | The filled new form when the steps for a Target DocType are done (desk) |
| `workflows/sessions.py` | Portal and WhatsApp conversations, found by the channel's own id |
| `workflows/desk.py` | What the panel shows: startable workflows, the progress bar, quick replies |
| `api/workflows.py` | `start_workflow`, `exit_workflow`; answers go through `chat.send_message` |
