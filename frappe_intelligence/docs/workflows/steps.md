# Steps, answers and the record

State lives on the **AI Conversation**: `workflow`, `current_step`, `collected_data` (`{step key: {field key: value}}`) and `status`.

## A step

| Field | Use |
|---|---|
| Step Order | Order of the steps; also "Step 2 of 4" |
| Step Key | Identifier; shown readable as the step's name |
| Prompt To User | The step's question, asked without AI when the step starts |
| Required Fields | `{field key: label}`; keys are the Target DocType's field names |
| Target DocType | The record the answers fill |
| Completion Check | Optional dotted path to a function in an installed app |
| Next Step Key | Jump to this step; empty means the next by order |

A step without Prompt To User asks "Please tell me: …" with its labels. A step without required fields is complete after any in-scope answer.

## Completion check

```python
def check(values: dict, collected: dict) -> bool | str:
	# values: this step's answers; collected: every step's answers
	return True  # move on; False or a message keeps the user on the step
```

A message is passed to the model, which asks the user to correct the answers; the next answer is read into all of the step's fields, so the correction replaces them. On WhatsApp the message is sent before the step's question. A path outside the installed apps is ignored and logged; a check that raises keeps the user on the step and is logged.

## Moving on

| Situation | Result |
|---|---|
| Step complete | `current_step` = Next Step Key, else the next by order |
| No next step (or Next Step Key not found) | Status Completed |
| Current step removed from the workflow | Status Abandoned |
| Idle 7 days while Active | Abandoned (`tasks.expire_old_sessions`) |

## The record

On the desk, when a step with a Target DocType is done and the next step has a different one (or there is none), a **new form** opens filled with the answers of every step for that DocType. Field keys are matched to writable fields by name or label (`utils/fields.writable_fieldname`); others are left out. The user checks and saves it: nothing is saved for them. It needs create permission on the DocType. The reply ends with "I opened a new … with these details. Check it and save it."
