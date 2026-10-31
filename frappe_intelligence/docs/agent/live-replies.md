# Live replies (`agent/runs.py`)

Answers run in a background job, so slow models never hit the web request timeout. The browser follows the job through realtime events and can stop it.

## Flow

```
send_message(message, conversation, context)
  → user message saved, AI Conversation.active_run = run_id
  → frappe.enqueue("agent.runs.execute", queue="long", timeout=1500, job_id=run_id)
  ← {conversation, run_id}                         # returns immediately

worker: runs.execute(conversation, run_id)
  → loop.run_turn(conversation, Hooks(...))
      text deltas → "text" events (batched)
      each tool   → "step" running, then done / failed / stopped
      after every model turn and tool batch → conversation saved and committed
  → active_run cleared → "done" event
```

Background workers must run the current code. After `bench update`, restart them (`bench restart` in production, or restart `bench start` in development); a worker started before the update fails every job.

## Events

All events use the realtime event **`fi_assistant`**, are sent only to the conversation's owner, and carry `run_id` and `conversation`. A page applies only events whose `run_id` it started.

| `type` | Fields | Notes |
|---|---|---|
| `text` | `text` | Answer text so far since the last event. Batched: sent every 0.15 s or 200 characters |
| `step` | `call_id`, `tool`, `label`, `status` | `status`: `running`, `done`, `failed`, `stopped`. `label` is translated, e.g. "Reading Customer list" |
| `done` | `reply`, `actions`, `steps`, `error`, `stopped` | Always the last event of a run; `actions` are the browser actions to perform |

Between `send_message` and the first event the model is thinking (and, on a local model, this can take a while); show a waiting state.

## Stop

`stop_message(conversation, run_id)` sets a Redis flag the job reads at most twice a second.

| Stopped while | Result |
|---|---|
| the model is writing | Generation is cut off; the text written so far is kept as the reply |
| tools are running | The current tool finishes; every remaining call gets "Stopped by the user before this ran." so the history stays valid for the next turn |
| before the next model call | No further call |

The run still ends with `done`, marked `stopped: true`.

## One run per conversation

`send_message` refuses a new message while the conversation's run is queued or running (`runs.ensure_idle`). Running means `active_run` is set **and** its job is queued or started, so a run whose worker died does not block the conversation.

## After a reload

`get_conversation` returns `active_run` while a run is in progress. Steps and tool results are saved as they happen, so the page can show them and keep listening for that `run_id`; text streamed before the reload arrives in the stored reply when the run ends.

## Code

| Piece | Responsibility |
|---|---|
| `runs.start` / `runs.execute` | Enqueue; the job itself |
| `runs.Stream` | Publishes `text`, `step`, `done`; batches text |
| `runs.StopFlag` | Throttled Stop check passed to the loop |
| `loop.Hooks` | `on_text`, `on_step`, `should_stop`, `checkpoint` — how any caller follows and controls a turn |
| `tests/test_runs.py` | Events, batching, Stop flag, job outcomes |
