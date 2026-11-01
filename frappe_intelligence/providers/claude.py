"""Anthropic Claude through the official SDK: streaming, tools, prompt caching and refusal fallback."""

from __future__ import annotations

import anthropic

from frappe_intelligence.providers.base import Message, Provider, Reply, ToolCall

MAX_OUTPUT_TOKENS = 32000
JSON_RETRIES = 2
CACHE = {"type": "ephemeral"}

# Models that accept server-side refusal fallback, routed by refusal category.
FALLBACK_MODELS = {
	"claude-fable-5-1",
	"claude-fable-5",
	"claude-opus-5-5",
	"claude-opus-5",
	"claude-sonnet-5-5",
}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# The 400 for thinking blocks replayed after the history before them changed.
STALE_THINKING = "bound to a different conversation"
THINKING_BLOCKS = {"thinking", "redacted_thinking"}

_STOP_REASONS = {"tool_use": "tool_calls", "max_tokens": "length", "refusal": "refusal"}
_ERROR_KINDS = (
	(anthropic.AuthenticationError, "auth"),
	(anthropic.NotFoundError, "model"),
	(anthropic.RateLimitError, "rate_limit"),
	(anthropic.APITimeoutError, "timeout"),
	(anthropic.APIConnectionError, "connection"),
)


class ClaudeProvider(Provider):
	name = "Claude"
	settings_prefix = "claude"
	default_model = "claude-opus-5-5"

	def complete(self, messages, *, system=None, tools=None, on_text=None, json_mode=False) -> Reply:
		self.ensure_configured()
		if json_mode:
			system = "\n\n".join(
				filter(None, [system, "Respond with a single JSON object and nothing else."])
			)
		params = {
			"model": self.config.model,
			"max_tokens": MAX_OUTPUT_TOKENS,
			"messages": self._messages(messages),
		}
		if system:
			params["system"] = [{"type": "text", "text": system, "cache_control": CACHE}]
		if tools:
			params["tools"] = [_tool(t) for t in tools]
		return self._reply(self._stream(params, on_text))

	def _stream(self, params: dict, on_text):
		client = anthropic.Anthropic(api_key=self.config.api_key, timeout=self.config.timeout)
		api = client.messages
		if self.config.model in FALLBACK_MODELS:
			api = client.beta.messages
			params = {**params, "betas": [FALLBACK_BETA], "fallbacks": "default"}
		try:
			return self._send(api, params, on_text)
		except anthropic.BadRequestError:
			# The history changed after Claude reasoned over it (an edited AI Settings prompt, say):
			# answer without that earlier reasoning.
			return self._send(api, {**params, "messages": _without_thinking(params["messages"])}, on_text)

	def _send(self, api, params: dict, on_text):
		for attempt in range(JSON_RETRIES + 1):
			try:
				with api.stream(**params) as stream:
					for event in stream:
						if event.type == "text" and on_text:
							on_text(event.text)
					return stream.get_final_message()
			except ValueError:
				# Tool input the SDK could not parse at all: there is no tool_use id to answer, so re-issue the turn.
				if attempt == JSON_RETRIES:
					raise self.error("cut_off") from None
			except anthropic.APIError as exc:
				if _stale_thinking(exc, params["messages"]):
					raise
				raise self.error_from(exc, _ERROR_KINDS) from exc

	def _reply(self, response) -> Reply:
		content = _replayable(response.content)
		stop_reason = _STOP_REASONS.get(response.stop_reason, "end")
		if stop_reason == "refusal":
			# A refusal can cut a tool call off mid-input; keep it out of the replayed turn too.
			content = [block for block in content if block.type != "tool_use"]
		return self.checked(
			Reply(
				text="".join(block.text for block in content if block.type == "text"),
				tool_calls=[
					ToolCall(id=block.id, name=block.name, arguments=_dict(block.input))
					for block in content
					if block.type == "tool_use"
				],
				stop_reason=stop_reason,
				raw=[block.model_dump(mode="json", exclude_none=True) for block in content],
				raw_provider=self.name,
				usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
			)
		)

	def _messages(self, messages: list[Message]) -> list[dict]:
		converted: list[dict] = []
		for message in messages:
			if message.role == "tool":
				result = {
					"type": "tool_result",
					"tool_use_id": message.tool_call_id,
					"content": message.content,
				}
				previous = converted[-1] if converted else None
				if previous and previous["role"] == "user" and _is_tool_results(previous["content"]):
					previous["content"].append(result)
				else:
					converted.append({"role": "user", "content": [result]})
			elif message.role == "assistant":
				content = (
					message.raw if message.raw_provider == self.name and message.raw else _blocks(message)
				)
				if content:
					converted.append({"role": "assistant", "content": content})
			else:
				converted.append({"role": "user", "content": message.content})
		_cache_last_turn(converted)
		return converted


def _tool(tool: dict) -> dict:
	return {
		"name": tool["name"],
		"description": tool["description"],
		"input_schema": tool["parameters"],
		"eager_input_streaming": True,
	}


def _dict(value) -> dict:
	"""The SDK's tolerant parser can hand back a partial or mistyped input."""
	return value if isinstance(value, dict) else {}


def _blocks(message: Message) -> list[dict]:
	blocks = [{"type": "text", "text": message.content}] if message.content else []
	return blocks + [
		{"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments}
		for call in message.tool_calls
	]


def _is_tool_results(content) -> bool:
	return isinstance(content, list) and bool(content) and content[-1].get("type") == "tool_result"


def _cache_last_turn(converted: list[dict]) -> None:
	"""Cache the conversation so far; the system prompt carries the other breakpoint."""
	if not converted or converted[-1]["role"] != "user":
		return
	content = converted[-1]["content"]
	if isinstance(content, str):
		converted[-1]["content"] = [{"type": "text", "text": content, "cache_control": CACHE}]
	else:
		content[-1] = {**content[-1], "cache_control": CACHE}


def _stale_thinking(exc: anthropic.APIError, messages: list[dict]) -> bool:
	return (
		isinstance(exc, anthropic.BadRequestError)
		and STALE_THINKING in str(exc)
		and any(
			block.get("type") in THINKING_BLOCKS
			for message in messages
			if message["role"] == "assistant"
			for block in message["content"]
		)
	)


def _without_thinking(messages: list[dict]) -> list[dict]:
	"""Assistant turns keep their text and tool calls; one left empty is dropped."""
	stripped = []
	for message in messages:
		if message["role"] == "assistant":
			message = {
				**message,
				"content": [
					block for block in message["content"] if block.get("type") not in THINKING_BLOCKS
				],
			}
			if not message["content"]:
				continue
		stripped.append(message)
	return stripped


def _replayable(content: list) -> list:
	"""After a mid-reply fallback, only text from before the last `fallback` block may be sent back."""
	boundary = max((i for i, block in enumerate(content) if block.type == "fallback"), default=-1)
	return [
		block for i, block in enumerate(content) if i > boundary or (i < boundary and block.type == "text")
	]
