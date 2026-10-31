"""OpenAI Chat Completions, and any server that speaks the same API (Azure, OpenRouter, Groq, vLLM, Ollama)."""

from __future__ import annotations

import json

import openai

from frappe_intelligence.providers.base import Message, Provider, Reply, ToolCall, parse_arguments

_STOP_REASONS = {"tool_calls": "tool_calls", "length": "length", "content_filter": "refusal"}
_ERROR_KINDS = (
	(openai.AuthenticationError, "auth"),
	(openai.NotFoundError, "model"),
	(openai.RateLimitError, "rate_limit"),
	(openai.APITimeoutError, "timeout"),
	(openai.APIConnectionError, "connection"),
)


class OpenAIProvider(Provider):
	name = "OpenAI"
	settings_prefix = "openai"
	default_base_url = "https://api.openai.com/v1"

	def complete(self, messages, *, system=None, tools=None, on_text=None, json_mode=False) -> Reply:
		self.ensure_configured()
		params = {"model": self.config.model, "messages": self._messages(messages, system), "stream": True}
		if tools:
			params["tools"] = [_tool(t) for t in tools]
		if json_mode:
			params["response_format"] = {"type": "json_object"}

		text, calls, finish_reason = [], {}, None
		try:
			for chunk in self._client().chat.completions.create(**params):
				if not chunk.choices:
					continue
				choice = chunk.choices[0]
				finish_reason = choice.finish_reason or finish_reason
				if choice.delta.content:
					text.append(choice.delta.content)
					if on_text:
						on_text(choice.delta.content)
				for delta in choice.delta.tool_calls or []:
					call = calls.setdefault(delta.index, {"id": "", "name": "", "arguments": ""})
					call["id"] = delta.id or call["id"]
					if delta.function:
						call["name"] += delta.function.name or ""
						call["arguments"] += delta.function.arguments or ""
		except openai.APIError as exc:
			raise self.error_from(exc, _ERROR_KINDS) from exc

		return self.checked(
			Reply(
				text="".join(text),
				tool_calls=[
					ToolCall(id=call["id"], name=call["name"], arguments=parse_arguments(call["arguments"]))
					for _, call in sorted(calls.items())
				],
				stop_reason=_STOP_REASONS.get(finish_reason, "tool_calls" if calls else "end"),
			)
		)

	def _client(self) -> openai.OpenAI:
		return openai.OpenAI(
			api_key=self.config.api_key,
			base_url=self.config.base_url,
			timeout=self.config.timeout,
		)

	@staticmethod
	def _messages(messages: list[Message], system: str | None) -> list[dict]:
		converted = [{"role": "system", "content": system}] if system else []
		for message in messages:
			if message.role == "tool":
				converted.append(
					{"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
				)
			elif message.tool_calls:
				converted.append(
					{
						"role": "assistant",
						"content": message.content or None,
						"tool_calls": [
							{
								"id": call.id,
								"type": "function",
								"function": {"name": call.name, "arguments": json.dumps(call.arguments)},
							}
							for call in message.tool_calls
						],
					}
				)
			else:
				converted.append({"role": message.role, "content": message.content})
		return converted


def _tool(tool: dict) -> dict:
	return {
		"type": "function",
		"function": {
			"name": tool["name"],
			"description": tool["description"],
			"parameters": tool["parameters"],
		},
	}
