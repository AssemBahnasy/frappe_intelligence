# Provider interface

```python
from frappe_intelligence.providers import Message, ProviderError, get_provider

reply = get_provider().complete(
	[Message(role="user", content="How many open Sales Orders?")],
	system="You are the assistant for this site.",
	tools=[{"name": "count_documents", "description": "…", "parameters": {...JSON schema...}}],
	on_text=lambda chunk: ...,  # streamed text, optional
	json_mode=False,  # ask for a single JSON object
)
```

`complete()` runs **one** model turn. Looping over tool calls is the caller's job (the agent loop).

## Types (`providers/base.py`)

| Type | Fields |
|---|---|
| `Message` | `role` (`user`, `assistant`, `tool`), `content`, `tool_calls`, `tool_call_id` and `name` (tool turns), `raw` and `raw_provider` |
| `ToolCall` | `id`, `name`, `arguments` (always a dict) |
| `Reply` | `text`, `tool_calls`, `stop_reason` (`end`, `tool_calls`, `length`, `refusal`), `raw`, `raw_provider`, `usage` |

`reply.as_message()` turns a reply into the assistant `Message` to append to the conversation.

## Replaying provider state

Claude and Gemini return state that must be sent back unchanged on the next turn (Claude thinking blocks and signatures, Gemini thought signatures). Each provider stores its own form in `Reply.raw` with `raw_provider` set to its name, and replays it only when the same provider handles the next turn. Any other provider rebuilds the turn from `content` and `tool_calls`.

Claude accepts a thinking block only if the system prompt, the tools and every message before it are unchanged since it was made; the conversation keeps its history that way ([agent/conversations.md](../agent/conversations.md#history-sent-to-the-model)). If something before the block did change, the API answers 400 "bound to a different conversation"; the provider then sends the turn again once with every `thinking` and `redacted_thinking` block removed (`_without_thinking`), so the model answers without that earlier reasoning instead of failing.

## Safety rules every provider follows

`Provider.checked()` is applied to every reply:

- A tool call that may have been cut off (`stop_reason == "length"`) raises `ProviderError` instead of being returned.
- A refusal never carries tool calls.

Claude also follows the fallback echo rule: after a mid-reply fallback, only text from before the `fallback` block is kept in `raw`.

## Errors

Every failure is a `ProviderError` whose message is safe to show to users. Each provider maps its SDK exceptions to a shared kind (`auth`, `model`, `rate_limit`, `timeout`, `connection`, `other`), and `Provider.error()` holds the translated message for each kind, so the wording lives in one place.
