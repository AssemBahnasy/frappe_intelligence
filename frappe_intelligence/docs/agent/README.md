# Agent

The assistant on the desk is an agent: it asks the model, runs the tools the model calls, gives the results back, and repeats until the model answers in plain text.

```
api/chat.send_message                                              ← returns {conversation, run_id}
  → background job agent/runs.execute → agent/loop.run_turn(conversation, hooks)
      → providers.get_provider().complete(history, system, tools)   ← providers/
      → agent/tools.execute(call)                                     ← permission-checked tools
      → AI Conversation rows: user, assistant (+ tool calls), tool results
```

| Concern | Doc |
|---|---|
| The loop: steps, limits, errors, context | [loop.md](loop.md) |
| Live replies: background job, realtime events, Stop | [live-replies.md](live-replies.md) |
| Agent mode: change proposals and approvals | [approvals.md](approvals.md) |
| Attached files and document review | [../documents/review.md](../documents/review.md) |
| Tools: what exists, how they are declared, adding one | [tools.md](tools.md) |
| AI Conversation: storage, history sent to the model, retention | [conversations.md](conversations.md) |
| Access, permissions and rate limits | [security.md](security.md) |

## Modes

| Mode | Tools | Status |
|---|---|---|
| Ask | Read data, run reports, search knowledge, open pages and new forms | Built |
| Agent | Ask tools plus changes the user approves ([approvals.md](approvals.md)) | Built |
| Workflow | No tools: answers are read into the workflow's steps ([../workflows/README.md](../workflows/README.md)) | Built |

## Endpoints (`api/chat.py`)

| Endpoint | Purpose |
|---|---|
| `send_message(message, conversation=None, context=None, mode="Ask", attachments=None)` | Stores the message and answers it in a background job; creates the conversation when none is given; `mode` is `Ask` or `Agent`; `attachments` are file URLs read first. Returns `{conversation, run_id}`; the answer arrives as `fi_assistant` events |
| `decide_proposal(conversation, call_id, approve)` | Confirms or rejects a proposed change; returns `run_id` once nothing is left waiting |
| `stop_message(conversation, run_id)` | Stops a running answer |
| `get_conversation(name)` | One of the user's conversations as turns (question, steps, answer, actions, feedback, stopped), and `active_run` while one is running |
| `rate_reply(conversation, message, feedback)` | Thumbs up (`Good`) or down (`Bad`) on an answer; empty clears it |
| `list_conversations(limit=20)` | The user's recent desk conversations |

## Code map

| File | Responsibility |
|---|---|
| `agent/loop.py` | `run_turn()` and `Hooks` |
| `agent/runs.py` | Background job, realtime events, Stop |
| `agent/prompts.py` | System prompt and per-message notes |
| `agent/transcript.py` | Stored rows → turns for the panel |
| `agent/suggestions.py` | Starter questions by role |
| `agent/tools/__init__.py` | `AgentTool`, registry, `execute()` |
| `agent/tools/frappe_data.py` | Frappe's MCP data tools, reused |
| `agent/tools/reports.py` | `search_reports`, `run_report` |
| `agent/tools/knowledge.py` | `search_knowledge` (AI Knowledge Packs) |
| `agent/tools/desk.py` | Browser actions: `navigate`, `open_document`, `new_document`, `show_chart` |
| `agent/tools/changes.py` | Agent mode changes: create, update, delete, submit, cancel |
| `intelligence/doctype/ai_conversation/` | Conversation storage and history rebuild |
| `tests/test_agent.py` | Loop, Stop, dispatch, prompts and history tests over fakes |
| `tests/test_runs.py` | Background run tests over fakes |
