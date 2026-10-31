"""Agent loop, tool dispatch, prompts and conversation history over fakes; no site needed."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch

import frappe

from frappe_intelligence.agent import loop, prompts
from frappe_intelligence.agent.tools import AgentTool, ToolError, desk, execute
from frappe_intelligence.intelligence.doctype.ai_conversation.ai_conversation import AIConversation
from frappe_intelligence.providers import Message, ProviderError, Reply, ToolCall


class FakeConversation:
	mode = "Ask"

	def __init__(self, text="How many customers?", context=None):
		self.messages: list[Message] = [Message(role="user", content=text)]
		self.context = context
		self.errors: list[str] = []

	def current_question(self):
		return self.messages[0].content, self.context

	def add_reply(self, reply):
		self.messages.append(reply.as_message())

	def add_tool_result(self, call, content, is_error=False):
		self.messages.append(Message(role="tool", tool_call_id=call.id, name=call.name, content=content))

	def add_error(self, text):
		self.errors.append(text)

	def add_stopped(self):
		self.stopped = True

	def provider_messages(self):
		return list(self.messages)


class ScriptedProvider:
	"""Replays replies; a reply given as a list of strings is streamed chunk by chunk first."""

	def __init__(self, *replies):
		self.replies = list(replies)
		self.calls = []

	def complete(self, messages, on_text=None, **kwargs):
		self.calls.append((messages, kwargs))
		reply = self.replies.pop(0)
		if isinstance(reply, Exception):
			raise reply
		if isinstance(reply, list):
			for chunk in reply:
				on_text(chunk)
			return Reply(text="".join(reply))
		return reply


def run(provider, outcome=None, hooks=None, **conversation):
	conversation = FakeConversation(**conversation)
	outcome = outcome or NS(content='{"result": 3}', is_error=False, action=None)
	with (
		patch.object(loop, "get_provider", return_value=provider),
		patch.object(loop, "tools_for", return_value=[]),
		patch.object(loop, "step_label", side_effect=lambda name, arguments: f"label:{name}"),
		patch.object(loop, "execute", return_value=outcome) as execute_tool,
		patch.object(loop.prompts, "system_prompt", return_value="system"),
		patch.object(loop.prompts, "language_rule", return_value="Reply in English."),
		patch.object(loop, "_", side_effect=lambda text: text),
	):
		result = loop.run_turn(conversation, hooks)
	return result, conversation, execute_tool


def tool_call(call_id="c1", name="count_documents"):
	return ToolCall(id=call_id, name=name, arguments={"doctype": "Customer"})


class TestLoop(TestCase):
	def test_runs_tools_until_the_model_answers(self):
		provider = ScriptedProvider(
			Reply(tool_calls=[tool_call()], stop_reason="tool_calls"), Reply(text="There are 3.")
		)
		steps, checkpoints = [], []
		hooks = loop.Hooks(on_step=steps.append, checkpoint=lambda: checkpoints.append(1))
		result, conversation, execute_tool = run(provider, hooks=hooks)
		self.assertEqual(result.reply, "There are 3.")
		self.assertEqual([(s.tool, s.status) for s in result.steps], [("count_documents", "done")])
		self.assertEqual([s.status for s in steps], ["running", "done"])
		execute_tool.assert_called_once_with("count_documents", {"doctype": "Customer"}, "Ask")
		self.assertEqual([m.role for m in conversation.messages], ["user", "assistant", "tool", "assistant"])
		self.assertEqual(len(checkpoints), 3)

	def test_context_goes_on_the_current_message_only(self):
		provider = ScriptedProvider(Reply(text="ok"))
		run(provider, text="What is this?", context={"doctype": "Customer", "docname": "CUST-1"})
		messages, kwargs = provider.calls[0]
		self.assertIn("The user has Customer CUST-1 open.", messages[-1].content)
		self.assertTrue(messages[-1].content.endswith("What is this?"))
		self.assertEqual(kwargs["system"], "system")

	def test_streams_text(self):
		streamed = []
		result, _, _ = run(ScriptedProvider(["The", " answer"]), hooks=loop.Hooks(on_text=streamed.append))
		self.assertEqual((streamed, result.reply), (["The", " answer"], "The answer"))

	def test_browser_actions_are_collected(self):
		action = {"type": "open_form", "doctype": "Customer", "name": "CUST-1"}
		outcome = NS(content="{}", is_error=False, action=action)
		call = tool_call(name="open_document")
		provider = ScriptedProvider(Reply(tool_calls=[call], stop_reason="tool_calls"), Reply(text="Opened."))
		result, _, _ = run(provider, outcome)
		self.assertEqual(result.actions, [action])

	def test_provider_errors_are_returned_and_stored(self):
		result, conversation, _ = run(ScriptedProvider(ProviderError("Ollama is down")))
		self.assertEqual(result.error, "Ollama is down")
		self.assertEqual(conversation.errors, ["Ollama is down"])

	def test_stops_after_the_step_limit(self):
		provider = ScriptedProvider(
			*[Reply(tool_calls=[tool_call()], stop_reason="tool_calls")] * loop.MAX_STEPS
		)
		result, conversation, _ = run(provider)
		self.assertIn(str(loop.MAX_STEPS), result.reply)
		self.assertEqual(conversation.errors, [result.reply])


class TestStop(TestCase):
	def test_stop_mid_answer_keeps_the_streamed_text(self):
		streamed = []
		hooks = loop.Hooks(on_text=streamed.append, should_stop=lambda: bool(streamed))
		result, conversation, _ = run(ScriptedProvider(["Partial", " never sent"]), hooks=hooks)
		self.assertTrue(result.stopped and conversation.stopped)
		self.assertEqual(streamed, ["Partial"])
		self.assertEqual(conversation.messages[-1].content, "Partial")

	def test_stop_between_tools_answers_every_pending_call(self):
		calls = [tool_call("c1"), tool_call("c2")]
		executed = []
		hooks = loop.Hooks(
			should_stop=lambda: bool(executed),
			on_step=lambda step: executed.append(step.status == "done") if step.status == "done" else None,
		)
		result, conversation, execute_tool = run(
			ScriptedProvider(Reply(tool_calls=calls, stop_reason="tool_calls")), hooks=hooks
		)
		self.assertTrue(result.stopped)
		execute_tool.assert_called_once()
		results = [m for m in conversation.messages if m.role == "tool"]
		self.assertEqual([m.tool_call_id for m in results], ["c1", "c2"])
		self.assertEqual(results[1].content, loop.STOPPED_RESULT)
		self.assertEqual([s.status for s in result.steps], ["done", "stopped"])

	def test_stop_before_the_first_model_call(self):
		provider = ScriptedProvider(Reply(text="unused"))
		result, conversation, _ = run(provider, hooks=loop.Hooks(should_stop=lambda: True))
		self.assertTrue(result.stopped)
		self.assertEqual(provider.calls, [])


class TestExecute(TestCase):
	def setUp(self):
		patcher = patch("frappe_intelligence.agent.tools._", side_effect=lambda text: text)
		patcher.start()
		self.addCleanup(patcher.stop)

	def with_tool(self, run, **kwargs):
		tool = AgentTool(
			name="probe", description="", parameters={}, run=run, label="Probing {doctype}", **kwargs
		)
		return patch("frappe_intelligence.agent.tools.registry", return_value={"probe": tool})

	def test_results_are_json(self):
		with self.with_tool(lambda args: {"count": 2}):
			outcome = execute("probe", {"doctype": "Item"}, "Ask")
		self.assertEqual((outcome.content, outcome.is_error), ('{"count": 2}', False))

	def test_tool_errors_reach_the_model(self):
		def fail(args):
			raise ToolError("Unknown field: colour")

		with self.with_tool(fail):
			outcome = execute("probe", {}, "Ask")
		self.assertEqual((outcome.content, outcome.is_error), ("Unknown field: colour", True))

	def test_permission_errors_reach_the_model_without_a_dialog(self):
		def deny(args):
			raise frappe.PermissionError("<b>Insufficient Permission</b> for Error Log")

		with self.with_tool(deny), patch("frappe_intelligence.agent.tools.frappe.clear_messages") as clear:
			outcome = execute("probe", {}, "Ask")
		self.assertEqual((outcome.content, outcome.is_error), ("Insufficient Permission for Error Log", True))
		clear.assert_called_once()

	def test_unexpected_errors_are_logged_not_shown(self):
		def crash(args):
			raise KeyError("secret internals")

		with self.with_tool(crash), patch("frappe_intelligence.agent.tools.frappe.log_error") as log:
			outcome = execute("probe", {}, "Ask")
		self.assertTrue(outcome.is_error)
		self.assertNotIn("secret", outcome.content)
		log.assert_called_once()

	def test_tools_outside_the_mode_are_refused(self):
		with self.with_tool(lambda args: {}, modes=frozenset({"Agent"})):
			self.assertTrue(execute("probe", {}, "Ask").is_error)


class TestDeskTools(TestCase):
	def setUp(self):
		patcher = patch.object(desk, "_", side_effect=lambda text: text)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_navigate_only_opens_desk_routes(self):
		self.assertEqual(
			desk.navigate({"route": "/app/item"})["action"], {"type": "set_route", "route": "/app/item"}
		)
		for route in ("https://evil.example", "/app//x", "javascript:alert(1)", "/login"):
			with self.assertRaises(ToolError):
				desk.navigate({"route": route})

	def test_chart_needs_one_number_per_label(self):
		chart = desk.show_chart({"labels": ["Q3", "Q4"], "datasets": [{"name": "Sales", "values": [10, 12]}]})
		self.assertEqual(chart["action"]["chart_type"], "bar")
		with self.assertRaises(ToolError):
			desk.show_chart({"labels": ["Q3", "Q4"], "datasets": [{"values": [10]}]})
		with self.assertRaises(ToolError):
			desk.show_chart({"labels": ["Q3"], "datasets": [{"values": [1]}], "type": "radar"})


class TestPrompts(TestCase):
	def test_page_notes(self):
		self.assertEqual(prompts.page_note(None), "")
		self.assertEqual(prompts.page_note({"doctype": "Item"}), "The user is viewing the Item list.")
		self.assertIn(
			'[["status","=","Open"]]',
			prompts.page_note({"doctype": "Task", "list_filters": [["status", "=", "Open"]]}),
		)
		self.assertEqual(
			prompts.page_note({"doctype": "Task", "docname": "T-1", "tab": "Details"}),
			"The user has Task T-1 open, on the Details tab.",
		)


class TestConversationHistory(TestCase):
	@staticmethod
	def row(role, **fields):
		return frappe._dict({"role": role, "content": role, "is_error": 0, **fields})

	def history(self, rows, limit=None):
		target = "frappe_intelligence.intelligence.doctype.ai_conversation.ai_conversation.HISTORY_LIMIT"
		with patch(target, limit or 40):
			return AIConversation.provider_messages(NS(messages=rows))

	def test_rebuilds_tool_turns_and_skips_error_notices(self):
		call = {"id": "c1", "name": "count_documents", "arguments": {"doctype": "Item"}}
		rows = [
			self.row("user"),
			self.row(
				"assistant",
				content="",
				tool_calls=json.dumps([call]),
				raw='[{"type": "tool_use"}]',
				raw_provider="Claude",
			),
			self.row("tool", tool_call_id="c1", tool_name="count_documents", content="3"),
			self.row("assistant", content="Ollama is down", is_error=1),
		]
		messages = self.history(rows)
		self.assertEqual([m.role for m in messages], ["user", "assistant", "tool"])
		self.assertEqual(messages[1].tool_calls, [ToolCall(**call)])
		self.assertEqual((messages[1].raw, messages[1].raw_provider), ([{"type": "tool_use"}], "Claude"))
		self.assertEqual((messages[2].tool_call_id, messages[2].name), ("c1", "count_documents"))

	def test_trimmed_history_starts_at_a_user_message_and_keeps_the_current_turn(self):
		rows = [self.row("user"), self.row("assistant"), self.row("user", content="now")]
		rows += [self.row("tool", tool_call_id=str(i)) for i in range(5)]
		messages = self.history(rows, limit=3)
		self.assertEqual(messages[0].content, "now")
		self.assertEqual(len(messages), 6)
