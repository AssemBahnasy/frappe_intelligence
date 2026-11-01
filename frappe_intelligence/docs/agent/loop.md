# The loop (`agent/loop.py`)

`run_turn(conversation, hooks=None)` answers the conversation's latest user message (`conversation.current_question()`). The caller stores that message first and saves the conversation afterwards.

1. Ask the provider for one turn with the conversation history, the system prompt and the mode's tools.
2. Store the assistant turn. If it has no tool calls, its text is the reply.
3. Otherwise run every tool call, store each result, and go back to 1.

## Hooks

| Hook | Called |
|---|---|
| `on_text(delta)` | For every piece of streamed answer text |
| `on_step(step)` | When a tool starts (`running`) and ends (`done`, `failed`, `stopped`) |
| `should_stop()` | Before each model call, while text streams, and before each tool; `True` stops the turn |
| `checkpoint()` | After each model turn and each tool batch; the background job saves and commits here |

The result's `stopped` is true when the turn was stopped; see [live-replies.md](live-replies.md) for what is kept.

| Limit | Value | Behaviour |
|---|---|---|
| `MAX_STEPS` | 8 model turns | Stops and tells the user to ask it to continue |
| History | 40 messages (`HISTORY_LIMIT`) | Older messages stay stored, see [conversations.md](conversations.md) |

## Prompt layout (`agent/prompts.py`)

The **system prompt** never changes between turns, so providers can cache it:

1. Frappe's own agent instructions (`frappe.mcp.protocol.server_instructions`): site, signed-in user, installed apps, and **System Settings → AI Agents → Agent Instructions**.
2. The assistant's behaviour rules (look up before answering, read fields before filtering, link format).
3. The mode rule (Ask cannot change data).
4. **AI Settings → System Prompt**.

What changes per message goes on that user message, as `<note>` lines before the text:

- the page note, from the message's `context` (`doctype`, `docname`, `tab`, `list_filters`, `route`);
- the language rule from **AI Settings → Response Language** (`utils/language.py`).

The stored message keeps only what the user typed and its `context`. Every turn renders each user message again from those (`prompts.with_context`), so earlier messages go back exactly as they were first sent; see [conversations.md](conversations.md#history-sent-to-the-model).

## Errors

| Failure | Result |
|---|---|
| Provider fails (`ProviderError`) | `error` in the result; stored as an error notice that is never sent back to the model |
| Tool fails | The error text goes back to the model as the tool result so it can correct itself; see [tools.md](tools.md) |
| Refusal or empty answer | A short explanation instead of an empty reply |
