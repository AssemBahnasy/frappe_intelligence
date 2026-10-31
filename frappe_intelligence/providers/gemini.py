"""Google Gemini through the google-genai SDK: streaming and function calling."""

from __future__ import annotations

import httpx
from google import genai
from google.genai import errors, types

from frappe_intelligence.providers.base import Message, Provider, Reply, ToolCall

# Gemini may omit call ids; ours carry this prefix and are not sent back.
LOCAL_ID_PREFIX = "fi-call-"

_REFUSALS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}
_ERROR_CODES = {400: "other", 401: "auth", 403: "auth", 404: "model", 429: "rate_limit"}
_ERROR_KINDS = ((httpx.TimeoutException, "timeout"), (httpx.TransportError, "connection"))


class GeminiProvider(Provider):
	name = "Gemini"
	settings_prefix = "gemini"
	default_model = "gemini-2.0-flash"

	def complete(self, messages, *, system=None, tools=None, on_text=None, json_mode=False) -> Reply:
		self.ensure_configured()
		config = types.GenerateContentConfig(
			system_instruction=system or None,
			tools=[types.Tool(function_declarations=[_declaration(t) for t in tools])] if tools else None,
			response_mime_type="application/json" if json_mode and not tools else None,
		)
		text, calls, parts, finish = [], [], [], None
		try:
			stream = self._client().models.generate_content_stream(
				model=self.config.model, contents=self._contents(messages), config=config
			)
			for chunk in stream:
				candidate = chunk.candidates[0] if chunk.candidates else None
				if not candidate:
					continue
				finish = candidate.finish_reason or finish
				for part in (candidate.content and candidate.content.parts) or []:
					parts.append(part)
					if part.function_call:
						calls.append(_call(part.function_call, len(calls)))
					elif part.text and not part.thought:
						text.append(part.text)
						if on_text:
							on_text(part.text)
		except errors.APIError as exc:
			raise self.error(_ERROR_CODES.get(exc.code, "other"), exc.message or str(exc)) from exc
		except httpx.HTTPError as exc:
			raise self.error_from(exc, _ERROR_KINDS) from exc

		return self.checked(
			Reply(
				text="".join(text),
				tool_calls=calls,
				stop_reason=_stop_reason(finish, calls),
				raw=[part.model_dump(mode="json", exclude_none=True) for part in parts],
				raw_provider=self.name,
			)
		)

	def _client(self) -> genai.Client:
		return genai.Client(
			api_key=self.config.api_key,
			http_options=types.HttpOptions(timeout=self.config.timeout * 1000),
		)

	def _contents(self, messages: list[Message]) -> list[types.Content]:
		contents: list[types.Content] = []
		for message in messages:
			if message.role == "tool":
				part = types.Part(function_response=_function_response(message))
				previous = contents[-1] if contents else None
				if previous and previous.role == "user" and previous.parts[-1].function_response:
					previous.parts.append(part)
				else:
					contents.append(types.Content(role="user", parts=[part]))
			elif message.role == "assistant":
				parts = self._model_parts(message)
				if parts:
					contents.append(types.Content(role="model", parts=parts))
			else:
				contents.append(
					types.Content(role="user", parts=[types.Part.from_text(text=message.content)])
				)
		return contents

	def _model_parts(self, message: Message) -> list[types.Part]:
		if message.raw_provider == self.name and message.raw:
			return [types.Part.model_validate(part) for part in message.raw]
		parts = [types.Part.from_text(text=message.content)] if message.content else []
		return parts + [
			types.Part(
				function_call=types.FunctionCall(id=_sent_id(call.id), name=call.name, args=call.arguments)
			)
			for call in message.tool_calls
		]


def _declaration(tool: dict) -> types.FunctionDeclaration:
	return types.FunctionDeclaration(
		name=tool["name"],
		description=tool["description"],
		parameters_json_schema=tool["parameters"],
	)


def _call(function_call: types.FunctionCall, index: int) -> ToolCall:
	return ToolCall(
		id=function_call.id or f"{LOCAL_ID_PREFIX}{index}",
		name=function_call.name,
		arguments=dict(function_call.args or {}),
	)


def _function_response(message: Message) -> types.FunctionResponse:
	return types.FunctionResponse(
		id=_sent_id(message.tool_call_id),
		name=message.name,
		response={"result": message.content},
	)


def _sent_id(call_id: str | None) -> str | None:
	return None if not call_id or call_id.startswith(LOCAL_ID_PREFIX) else call_id


def _stop_reason(finish, calls: list[ToolCall]) -> str:
	reason = getattr(finish, "name", finish)
	if reason == "MAX_TOKENS":
		return "length"
	if reason in _REFUSALS:
		return "refusal"
	return "tool_calls" if calls else "end"
