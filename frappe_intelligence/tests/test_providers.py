"""Provider layer tests. They use fake SDK clients, so they need no API keys and no site."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

import anthropic
import httpx
import openai
from google.genai import types

from frappe_intelligence.providers import (
	FallbackProvider,
	Message,
	ProviderConfig,
	ProviderError,
	ToolCall,
	build,
)
from frappe_intelligence.providers.claude import FALLBACK_BETA, ClaudeProvider
from frappe_intelligence.providers.gemini import LOCAL_ID_PREFIX, GeminiProvider
from frappe_intelligence.providers.ollama import OllamaProvider
from frappe_intelligence.providers.openai import OpenAIProvider

NESTED_SCHEMA = {
	"type": "object",
	"properties": {
		"defaults": {
			"type": "object",
			"properties": {"items": {"type": "array", "items": {"type": "object"}}},
		}
	},
}
TOOLS = [{"name": "list_records", "description": "List records", "parameters": NESTED_SCHEMA}]
CONVERSATION = [
	Message(role="user", content="How many open orders?"),
	Message(
		role="assistant",
		tool_calls=[ToolCall(id="c1", name="list_records", arguments={"doctype": "Sales Order"})],
	),
	Message(role="tool", tool_call_id="c1", name="list_records", content='{"count": 3}'),
]


class ProviderTestCase(TestCase):
	def setUp(self):
		for target in ("frappe_intelligence.providers.base._",):
			patcher = patch(target, side_effect=lambda text: text)
			patcher.start()
			self.addCleanup(patcher.stop)

	@staticmethod
	def config(**overrides) -> ProviderConfig:
		return ProviderConfig(**{"model": "test-model", "api_key": "key", "timeout": 30, **overrides})


class TestOpenAIProvider(ProviderTestCase):
	def provider(self, chunks):
		provider = OpenAIProvider(self.config(base_url="https://api.openai.com/v1"))
		client = MagicMock()
		client.chat.completions.create.return_value = iter(chunks)
		provider._client = lambda: client
		return provider, client

	@staticmethod
	def chunk(content=None, tool_calls=None, finish_reason=None):
		return NS(choices=[NS(delta=NS(content=content, tool_calls=tool_calls), finish_reason=finish_reason)])

	@staticmethod
	def call_delta(index, id=None, name=None, arguments=None):
		return NS(index=index, id=id, function=NS(name=name, arguments=arguments))

	def test_streams_text_and_joins_tool_call_fragments(self):
		provider, _ = self.provider(
			[
				self.chunk("Hel"),
				self.chunk("lo"),
				self.chunk(tool_calls=[self.call_delta(0, id="c1", name="list_", arguments='{"a"')]),
				self.chunk(
					tool_calls=[self.call_delta(0, name="records", arguments=": 1}")],
					finish_reason="tool_calls",
				),
			]
		)
		streamed = []
		reply = provider.complete([Message(role="user", content="hi")], on_text=streamed.append)
		self.assertEqual(streamed, ["Hel", "lo"])
		self.assertEqual(reply.text, "Hello")
		self.assertEqual(reply.tool_calls, [ToolCall(id="c1", name="list_records", arguments={"a": 1})])
		self.assertEqual(reply.stop_reason, "tool_calls")

	def test_sends_system_tool_calls_and_tool_results(self):
		provider, client = self.provider([self.chunk("3 orders", finish_reason="stop")])
		provider.complete(CONVERSATION, system="Be brief", tools=TOOLS, json_mode=True)
		params = client.chat.completions.create.call_args.kwargs
		self.assertEqual(params["messages"][0], {"role": "system", "content": "Be brief"})
		self.assertEqual(
			params["messages"][2]["tool_calls"][0]["function"]["arguments"], '{"doctype": "Sales Order"}'
		)
		self.assertEqual(
			params["messages"][3], {"role": "tool", "tool_call_id": "c1", "content": '{"count": 3}'}
		)
		self.assertEqual(params["tools"][0]["function"]["parameters"], NESTED_SCHEMA)
		self.assertEqual(params["response_format"], {"type": "json_object"})

	def test_cut_off_tool_call_is_never_returned(self):
		provider, _ = self.provider(
			[
				self.chunk(
					tool_calls=[self.call_delta(0, id="c1", name="x", arguments='{"a"')],
					finish_reason="length",
				)
			]
		)
		with self.assertRaises(ProviderError):
			provider.complete([Message(role="user", content="hi")])

	def test_sdk_errors_become_readable(self):
		provider, client = self.provider([])
		response = httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1"))
		client.chat.completions.create.side_effect = openai.AuthenticationError(
			"bad", response=response, body=None
		)
		with self.assertRaisesRegex(ProviderError, "rejected the API key"):
			provider.complete([Message(role="user", content="hi")])

	def test_missing_key_is_reported_before_calling(self):
		provider = OpenAIProvider(self.config(api_key=None))
		with self.assertRaisesRegex(ProviderError, "API key is not set"):
			provider.complete([Message(role="user", content="hi")])


class TestOllamaProvider(ProviderTestCase):
	def provider(self, **overrides):
		defaults = {"api_key": None, "base_url": "http://ollama:11434/", "model": "qwen2.5:7b"}
		return OllamaProvider(self.config(**{**defaults, **overrides}))

	def test_uses_the_openai_compatible_endpoint(self):
		client = self.provider()._client()
		self.assertEqual(str(client.base_url), "http://ollama:11434/v1/")

	def test_connection_names_a_model_that_is_not_pulled(self):
		tags = MagicMock(json=lambda: {"models": [{"name": "llama3:latest"}]})
		with patch("frappe_intelligence.providers.ollama.requests.request", return_value=tags):
			with self.assertRaisesRegex(ProviderError, "ollama pull qwen2.5:7b"):
				self.provider().test_connection()

	def test_keep_loaded_preloads_once(self):
		provider = self.provider(keep_loaded=True, model="phi4")
		with (
			patch("frappe_intelligence.providers.ollama.requests.request") as request,
			patch.object(OpenAIProvider, "complete") as complete,
		):
			provider.complete([])
			provider.complete([])
		request.assert_called_once()
		self.assertEqual(request.call_args.kwargs["json"], {"model": "phi4", "keep_alive": -1})
		self.assertEqual(complete.call_count, 2)


class Block(NS):
	def model_dump(self, **_):
		return dict(vars(self))


class TestClaudeProvider(ProviderTestCase):
	def run_claude(
		self, content, stop_reason="end_turn", model="claude-opus-5-5", messages=CONVERSATION, **kwargs
	):
		final = NS(content=content, stop_reason=stop_reason, usage=NS(input_tokens=10, output_tokens=5))
		client = MagicMock()

		@contextmanager
		def stream(**params):
			self.params = params
			yield MagicMock(
				__iter__=lambda _: iter([NS(type="text", text=b.text) for b in content if b.type == "text"]),
				get_final_message=lambda: final,
			)

		client.messages.stream.side_effect = stream
		client.beta.messages.stream.side_effect = stream
		with patch("frappe_intelligence.providers.claude.anthropic.Anthropic", return_value=client):
			reply = ClaudeProvider(self.config(model=model)).complete(messages, **kwargs)
		return reply, client

	def test_fallback_models_use_server_side_fallback(self):
		_, client = self.run_claude([Block(type="text", text="ok")])
		client.beta.messages.stream.assert_called_once()
		self.assertEqual(self.params["fallbacks"], "default")
		self.assertEqual(self.params["betas"], [FALLBACK_BETA])

	def test_other_models_use_the_plain_endpoint(self):
		_, client = self.run_claude([Block(type="text", text="ok")], model="claude-haiku-5-5")
		client.messages.stream.assert_called_once()
		self.assertNotIn("fallbacks", self.params)

	def test_caches_system_prompt_and_conversation_and_groups_tool_results(self):
		conversation = [*CONVERSATION, Message(role="tool", tool_call_id="c2", name="x", content="done")]
		self.run_claude(
			[Block(type="text", text="ok")], messages=conversation, system="Be brief", tools=TOOLS
		)
		self.assertEqual(self.params["system"][0]["cache_control"], {"type": "ephemeral"})
		self.assertEqual(self.params["tools"][0]["input_schema"], NESTED_SCHEMA)
		self.assertTrue(self.params["tools"][0]["eager_input_streaming"])
		last = self.params["messages"][-1]
		self.assertEqual([block["tool_use_id"] for block in last["content"]], ["c1", "c2"])
		self.assertEqual(last["content"][-1]["cache_control"], {"type": "ephemeral"})

	def test_replays_its_own_turns_unchanged(self):
		raw = [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": "Hi"}]
		history = [
			Message(role="user", content="a"),
			Message(role="assistant", content="Hi", raw=raw, raw_provider="Claude"),
		]
		self.run_claude(
			[Block(type="text", text="ok")], messages=[*history, Message(role="user", content="b")]
		)
		self.assertEqual(self.params["messages"][1]["content"], raw)

	def test_a_changed_history_is_answered_again_without_earlier_reasoning(self):
		raw = [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": "Hi"}]
		history = [
			Message(role="user", content="a"),
			Message(role="assistant", content="Hi", raw=raw, raw_provider="Claude"),
			Message(role="assistant", raw=raw[:1], raw_provider="Claude"),
			Message(role="user", content="b"),
		]
		response = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com"))
		stale = anthropic.BadRequestError(
			"messages.1.content.0: Invalid `signature` in `thinking` block. The block is bound to a "
			"different conversation.",
			response=response,
			body=None,
		)
		final = NS(
			content=[Block(type="text", text="ok")],
			stop_reason="end_turn",
			usage=NS(input_tokens=1, output_tokens=1),
		)
		sent = []

		@contextmanager
		def stream(**params):
			sent.append(params["messages"])
			if len(sent) == 1:
				raise stale
			yield MagicMock(__iter__=lambda _: iter([]), get_final_message=lambda: final)

		client = MagicMock()
		client.messages.stream.side_effect = stream
		with patch("frappe_intelligence.providers.claude.anthropic.Anthropic", return_value=client):
			reply = ClaudeProvider(self.config(model="claude-haiku-5-5")).complete(history)
		self.assertEqual(reply.text, "ok")
		self.assertEqual([m["role"] for m in sent[1]], ["user", "assistant", "user"])
		self.assertEqual(sent[1][1]["content"], [{"type": "text", "text": "Hi"}])

	def test_returns_tool_calls_with_raw_turn(self):
		content = [
			Block(type="text", text="Checking"),
			Block(type="tool_use", id="t1", name="list_records", input={"a": 1}),
		]
		reply, _ = self.run_claude(content, stop_reason="tool_use")
		self.assertEqual(reply.tool_calls, [ToolCall(id="t1", name="list_records", arguments={"a": 1})])
		self.assertEqual(reply.raw_provider, "Claude")
		self.assertEqual(reply.raw[1]["type"], "tool_use")

	def test_refusal_drops_tool_calls(self):
		content = [Block(type="tool_use", id="t1", name="x", input={})]
		reply, _ = self.run_claude(content, stop_reason="refusal")
		self.assertEqual((reply.stop_reason, reply.tool_calls, reply.raw), ("refusal", [], []))

	def test_after_a_fallback_only_earlier_text_is_replayed(self):
		content = [
			Block(type="thinking", thinking=""),
			Block(type="text", text="a"),
			Block(type="fallback"),
			Block(type="text", text="b"),
		]
		reply, _ = self.run_claude(content)
		self.assertEqual([block["text"] for block in reply.raw], ["a", "b"])

	def test_unparseable_tool_input_is_retried(self):
		calls = iter([ValueError("bad json"), None])
		final = NS(
			content=[Block(type="text", text="ok")],
			stop_reason="end_turn",
			usage=NS(input_tokens=1, output_tokens=1),
		)

		@contextmanager
		def stream(**_):
			error = next(calls)
			if error:
				raise error
			yield MagicMock(__iter__=lambda _: iter([]), get_final_message=lambda: final)

		client = MagicMock()
		client.messages.stream.side_effect = stream
		with patch("frappe_intelligence.providers.claude.anthropic.Anthropic", return_value=client):
			reply = ClaudeProvider(self.config(model="claude-haiku-5-5")).complete(
				[Message(role="user", content="hi")]
			)
		self.assertEqual(reply.text, "ok")

	def test_rate_limit_is_readable(self):
		response = httpx.Response(429, request=httpx.Request("POST", "https://api.anthropic.com"))
		client = MagicMock()
		client.messages.stream.side_effect = anthropic.RateLimitError(
			"slow down", response=response, body=None
		)
		with patch("frappe_intelligence.providers.claude.anthropic.Anthropic", return_value=client):
			with self.assertRaisesRegex(ProviderError, "rate limit"):
				ClaudeProvider(self.config(model="claude-haiku-5-5")).complete(
					[Message(role="user", content="hi")]
				)


class TestGeminiProvider(ProviderTestCase):
	def run_gemini(self, parts, messages=CONVERSATION, **kwargs):
		chunk = NS(candidates=[NS(finish_reason="STOP", content=NS(parts=parts))])
		client = MagicMock()
		client.models.generate_content_stream.return_value = iter([chunk])
		provider = GeminiProvider(self.config())
		provider._client = lambda: client
		return provider.complete(messages, **kwargs), client.models.generate_content_stream.call_args.kwargs

	def test_keeps_nested_tool_schemas(self):
		_, params = self.run_gemini([types.Part.from_text(text="ok")], tools=TOOLS)
		declaration = params["config"].tools[0].function_declarations[0]
		self.assertEqual(declaration.parameters_json_schema, NESTED_SCHEMA)

	def test_local_call_ids_are_not_sent_back(self):
		call = types.Part(function_call=types.FunctionCall(name="list_records", args={"doctype": "Item"}))
		reply, _ = self.run_gemini([call])
		self.assertTrue(reply.tool_calls[0].id.startswith(LOCAL_ID_PREFIX))
		self.assertEqual(reply.stop_reason, "tool_calls")

		answer = Message(role="tool", tool_call_id=reply.tool_calls[0].id, name="list_records", content="[]")
		_, params = self.run_gemini(
			[types.Part.from_text(text="none")], messages=[reply.as_message(), answer]
		)
		response = params["contents"][1].parts[0].function_response
		self.assertIsNone(response.id)
		self.assertEqual(response.response, {"result": "[]"})

	def test_streams_text_but_not_thoughts(self):
		streamed = []
		parts = [types.Part(text="thinking", thought=True), types.Part.from_text(text="answer")]
		reply, _ = self.run_gemini(parts, on_text=streamed.append)
		self.assertEqual((streamed, reply.text), (["answer"], "answer"))


class TestFallbackProvider(ProviderTestCase):
	def test_answers_from_fallback_when_primary_fails(self):
		primary, fallback = MagicMock(), MagicMock()
		primary.complete.side_effect = ProviderError("down")
		fallback.complete.return_value = "fallback reply"
		with patch("frappe_intelligence.providers.fallback.frappe.logger"):
			self.assertEqual(FallbackProvider(primary, fallback).complete([]), "fallback reply")

	def test_does_not_switch_after_text_was_streamed(self):
		def stream_then_fail(messages, on_text, **_):
			on_text("partial")
			raise ProviderError("dropped")

		primary, fallback = MagicMock(), MagicMock()
		primary.complete.side_effect = stream_then_fail
		with self.assertRaises(ProviderError):
			FallbackProvider(primary, fallback).complete([], on_text=lambda _: None)
		fallback.complete.assert_not_called()


class Settings(dict):
	def get_password(self, fieldname, raise_exception=True):
		return self.get(fieldname)


class TestRegistry(ProviderTestCase):
	def test_builds_from_settings_with_defaults(self):
		settings = Settings(openai_api_key="sk", openai_model="gpt-test", request_timeout=15)
		with patch("frappe_intelligence.providers.base.frappe.conf", {}):
			provider = build("OpenAI", settings)
		self.assertIsInstance(provider, OpenAIProvider)
		self.assertEqual(
			vars(provider.config),
			vars(
				ProviderConfig(
					model="gpt-test", api_key="sk", base_url="https://api.openai.com/v1", timeout=15
				)
			),
		)

	def test_local_provider_needs_no_key(self):
		with patch("frappe_intelligence.providers.base.frappe.conf", {}):
			provider = build("Ollama", Settings())
		self.assertEqual((provider.config.model, provider.config.api_key), ("qwen2.5:7b", None))
