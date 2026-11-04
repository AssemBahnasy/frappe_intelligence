"""Agent loop, tool dispatch, prompts and conversation history over fakes; no site needed."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_intelligence.agent import loop, prompts
from frappe_intelligence.agent.tools import AgentTool, Outcome, ToolError, changes, desk, execute
from frappe_intelligence.documents import review
from frappe_intelligence.intelligence.doctype.ai_conversation.ai_conversation import (
	MOVED_ON_RESULT,
	REJECTED_RESULT,
	AIConversation,
)
from frappe_intelligence.providers import Message, ProviderError, Reply, ToolCall
from frappe_intelligence.utils import language


class FakeConversation:
	mode = "Ask"

	def __init__(self, text="How many customers?", context=None, approved=None, attachments=None):
		self.messages: list[Message] = [Message(role="user", content=text)]
		self.context = context
		self.errors: list[str] = []
		self.proposals: list = []
		self.approved = approved or []
		self.attachments = attachments or []

	def add_proposal(self, call, preview, content=None):
		self.proposals.append((call.id, preview, content))

	def unread_attachments(self):
		calls = [
			ToolCall(id=f"read_{i}", name="read_document", arguments=file)
			for i, file in enumerate(self.attachments)
		]
		self.attachments = []
		return calls

	def approved_to_run(self):
		return self.approved

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

	def provider_messages(self, user_content=None, thinking=True):
		return [
			replace(message, content=user_content(message.content, self.context))
			if user_content and message.role == "user"
			else message
			for message in self.messages
		]


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


def run(provider, outcome=None, hooks=None, proposal=None, **conversation):
	conversation = FakeConversation(**conversation)
	outcome = outcome or Outcome(content='{"result": 3}')
	with (
		patch.object(loop, "needs_approval", side_effect=lambda name: name == "create_document"),
		patch.object(loop, "propose", return_value=proposal) as propose,
		patch.object(loop, "get_provider", return_value=provider),
		patch.object(loop, "tools_for", return_value=[]),
		patch.object(loop, "step_label", side_effect=lambda name, arguments: f"label:{name}"),
		patch.object(loop, "execute", return_value=outcome) as execute_tool,
		patch.object(loop.prompts, "system_prompt", return_value="system"),
		patch.object(loop.prompts, "language_rule", return_value="Reply in English."),
		patch.object(loop, "_", side_effect=lambda text: text),
	):
		result = loop.run_turn(conversation, hooks)
	run.propose = propose
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
		outcome = Outcome(content="{}", action=action)
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


class TestApprovals(TestCase):
	def test_a_change_pauses_the_turn_until_the_user_decides(self):
		call = tool_call(name="create_document")
		preview = {"title": "Create Payment Entry", "fields": []}
		reply = Reply(text="Here is the payment.", tool_calls=[call], stop_reason="tool_calls")
		provider = ScriptedProvider(reply)
		result, conversation, execute_tool = run(provider, proposal=NS(is_error=False, preview=preview))
		self.assertEqual(result.proposals, [{"call_id": "c1", "preview": preview}])
		self.assertEqual(result.reply, "Here is the payment.")
		self.assertEqual(conversation.proposals, [("c1", preview, None)])
		self.assertEqual(len(provider.calls), 1)
		execute_tool.assert_not_called()

	def test_an_invalid_change_goes_back_to_the_model(self):
		call = tool_call(name="create_document")
		provider = ScriptedProvider(
			Reply(tool_calls=[call], stop_reason="tool_calls"), Reply(text="Which customer?")
		)
		invalid = NS(is_error=True, content="customer: Field required", preview=None)
		result, conversation, _ = run(provider, proposal=invalid)
		self.assertEqual(result.proposals, [])
		self.assertEqual(result.reply, "Which customer?")
		tool_rows = [m for m in conversation.messages if m.role == "tool"]
		self.assertEqual(tool_rows[0].content, "customer: Field required")

	def test_approved_changes_run_before_the_model_is_asked(self):
		row = NS(content="", is_error=0)
		approved = [(row, tool_call(name="create_document"))]
		outcome = Outcome(content='{"created": "ACC-PAY-1"}')
		steps = []
		result, _, execute_tool = run(
			ScriptedProvider(Reply(text="Created ACC-PAY-1.")),
			outcome,
			loop.Hooks(on_step=steps.append),
			approved=approved,
		)
		execute_tool.assert_called_once_with("create_document", {"doctype": "Customer"}, "Ask")
		self.assertEqual(row.content, '{"created": "ACC-PAY-1"}')
		self.assertEqual([s.status for s in steps], ["running", "done"])
		self.assertEqual(result.reply, "Created ACC-PAY-1.")


FILE = {"file_url": "/private/files/bill.pdf", "file_name": "bill.pdf"}


class TestAttachments(TestCase):
	def test_files_are_read_before_the_model_is_asked(self):
		provider = ScriptedProvider(Reply(text="It is a bill from Gulf Pack."))
		result, conversation, execute_tool = run(provider, attachments=[FILE])
		execute_tool.assert_called_once_with("read_document", FILE, "Ask")
		self.assertEqual([m.role for m in conversation.messages], ["user", "assistant", "tool", "assistant"])
		self.assertEqual(conversation.messages[1].tool_calls[0].name, "read_document")
		self.assertEqual(len(provider.calls[0][0]), 3)  # the model sees the reading
		self.assertEqual(result.reply, "It is a bill from Gulf Pack.")

	def test_a_reading_to_review_pauses_before_the_model(self):
		card = {"kind": "review", "fields": []}
		outcome = Outcome(content='{"text": "GP-8841"}', review=card)
		provider = ScriptedProvider()
		result, conversation, _ = run(provider, outcome, attachments=[FILE])
		self.assertEqual(provider.calls, [])
		self.assertEqual(result.proposals, [{"call_id": "read_0", "preview": card}])
		self.assertEqual(conversation.proposals, [("read_0", card, '{"text": "GP-8841"}')])


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
		result, *_ = run(provider, hooks=loop.Hooks(should_stop=lambda: True))
		self.assertTrue(result.stopped)
		self.assertEqual(provider.calls, [])


class TestExecute(TestCase):
	def setUp(self):
		for target, kwargs in (
			("frappe_intelligence.agent.tools._", {"side_effect": lambda text: text}),
			("frappe_intelligence.agent.tools.frappe.db", {"new": MagicMock()}),
		):
			patcher = patch(target, **kwargs)
			self.db = patcher.start()
			self.addCleanup(patcher.stop)

	def test_a_failed_run_is_rolled_back(self):
		def fail(args):
			raise ToolError("Missing customer")

		with self.with_tool(fail):
			execute("probe", {}, "Ask")
		self.db.savepoint.assert_called_once()
		self.db.rollback.assert_called_once_with(save_point="fi_assistant_tool")

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

	def test_a_review_card_is_kept_out_of_the_result(self):
		with self.with_tool(lambda args: {"text": "x", "review": {"kind": "review"}}, review=True):
			outcome = execute("probe", {}, "Ask")
		self.assertEqual((outcome.content, outcome.review), ('{"text": "x"}', {"kind": "review"}))

	def test_step_labels_use_any_argument(self):
		tool = AgentTool(name="p", description="", parameters={}, run=None, label="Reading {file_name}")
		self.assertEqual(tool.step_label({"file_name": "bill.pdf"}), "Reading bill.pdf")
		self.assertEqual(tool.step_label({}), "Reading ")

	def test_step_labels_name_the_doctype_in_the_users_language(self):
		from frappe_intelligence.agent import tools

		tool = AgentTool(name="p", description="", parameters={}, run=None, label="Counting {doctype}")
		with patch.object(tools, "_", side_effect={"Customer": "العميل"}.get):
			self.assertEqual(tool.step_label({"doctype": "Customer"}), "Counting العميل")

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

	def test_fill_form_leaves_out_fields_the_doctype_lacks(self):
		fields = [
			NS(fieldname="supplier", label="Supplier", read_only=0),
			NS(fieldname="bill_no", label="Bill No", read_only=0),
			NS(fieldname="grand_total", label="Grand Total", read_only=1),
		]
		meta = NS(
			fields=fields, get_field=lambda name: next((f for f in fields if f.fieldname == name), None)
		)
		with (
			patch.object(desk.frappe, "has_permission"),
			patch.object(desk.frappe, "get_meta", return_value=meta),
		):
			values = {"supplier": "Gulf Pack", "Bill No": "GP-8841", "vendor_vat": "300", "grand_total": 9}
			result = desk.fill_form({"doctype": "Purchase Invoice", "values": values})
			self.assertEqual(result["action"]["values"], {"supplier": "Gulf Pack", "bill_no": "GP-8841"})
			self.assertIn("vendor_vat, grand_total", result["skipped"])
			with self.assertRaises(ToolError):
				desk.fill_form({"doctype": "Purchase Invoice", "values": {"vendor": "Gulf Pack"}})

	def test_chart_needs_one_number_per_label(self):
		chart = desk.show_chart({"labels": ["Q3", "Q4"], "datasets": [{"name": "Sales", "values": [10, 12]}]})
		self.assertEqual(chart["action"]["chart_type"], "bar")
		with self.assertRaises(ToolError):
			desk.show_chart({"labels": ["Q3", "Q4"], "datasets": [{"values": [10]}]})
		with self.assertRaises(ToolError):
			desk.show_chart({"labels": ["Q3"], "datasets": [{"values": [1]}], "type": "radar"})


class TestChangeTools(TestCase):
	def setUp(self):
		settings = NS(agent_excluded_doctypes=[NS(excluded_doctype="Item")])
		for target, kwargs in (
			("_", {"side_effect": lambda text: text}),
			("frappe.get_cached_doc", {"return_value": settings}),
			("_run_mcp", {"return_value": {"name": "T-1"}}),
		):
			patcher = patch(f"frappe_intelligence.agent.tools.changes.{target}", **kwargs)
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_settings_are_checked_again_when_the_change_runs(self):
		with patch.object(changes, "agent_mode_refusal", return_value=None):
			self.assertEqual(changes.run_create({"doctype": "ToDo", "data": {}})["created"], "T-1")
			for doctype in ("Item", "User"):
				with self.assertRaises(ToolError):
					changes.run_create({"doctype": doctype, "data": {}})
		with (
			patch.object(
				changes, "agent_mode_refusal", return_value="Agent mode is turned off in AI Settings."
			),
			self.assertRaises(ToolError),
		):
			changes.run_delete({"doctype": "ToDo", "name": "T-1"})


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
		self.assertIn(
			"new, unsaved Purchase Invoice form",
			prompts.page_note({"doctype": "Purchase Invoice", "new": True}),
		)

	def test_a_file_without_text_still_reads_as_a_message(self):
		with patch.object(prompts, "language_rule", return_value=""):
			self.assertTrue(prompts.with_context("", None).endswith(prompts.FILE_ONLY))


class TestReplyLanguage(TestCase):
	def test_replies_written_without_ai_follow_the_message_language(self):
		with patch.object(language, "allowed_languages", return_value=[]):
			self.assertEqual(language.reply_language("مرحبا"), "ar")
			frappe.local.lang = "en"
			with language.replying_to("مرحبا"):
				self.assertEqual(frappe.local.lang, "ar")
			self.assertEqual(frappe.local.lang, "en")
			self.assertEqual(language.reply_language("Hello"), "en")

	def test_ai_settings_languages_come_first(self):
		with patch.object(language, "allowed_languages", return_value=[("en", "English")]):
			self.assertEqual(language.reply_language("مرحبا"), "en")
			self.assertIn("English", language.language_rule("مرحبا"))


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
		messages = self.history(rows, limit=2)
		self.assertEqual(messages[0].content, "now")
		self.assertEqual(len(messages), 6)

	def test_the_window_holds_still_while_the_turn_runs(self):
		rows = [self.row("user"), self.row("assistant")] * 2 + [self.row("user", content="now")]
		before = self.history(rows, limit=4)
		rows += [self.row("tool", tool_call_id=str(i)) for i in range(5)]
		self.assertEqual(self.history(rows, limit=4)[: len(before)], before)
		self.assertEqual(len(before), 3)

	def test_earlier_messages_go_back_as_first_sent(self):
		rows = [
			self.row("user", content="a", context='{"doctype": "Item"}'),
			self.row("assistant", raw='[{"type": "thinking"}]', raw_provider="Claude"),
			self.row("user", content="b"),
		]
		messages = AIConversation.provider_messages(
			NS(messages=rows), lambda text, context: f"{text}|{context and context['doctype']}"
		)
		self.assertEqual([m.content for m in messages], ["a|Item", "assistant", "b|None"])
		self.assertEqual(messages[1].raw, [{"type": "thinking"}])

	def test_reasoning_is_left_out_before_a_trimmed_window_or_when_asked(self):
		thought = {"raw": '[{"type": "thinking"}]', "raw_provider": "Claude"}
		rows = [self.row("user"), self.row("assistant", **thought), self.row("user")]
		rows += [self.row("assistant", **thought), self.row("user"), self.row("assistant", **thought)]
		self.assertEqual(
			[m.raw for m in self.history(rows, limit=4) if m.role == "assistant"],
			[None, [{"type": "thinking"}]],
		)
		without = AIConversation.provider_messages(NS(messages=rows), thinking=False)
		self.assertEqual({m.raw for m in without if m.role == "assistant"}, {None})


class TestProposalRecords(TestCase):
	"""AI Conversation's proposal methods over plain rows."""

	@staticmethod
	def rows():
		call = {"id": "c1", "name": "create_document", "arguments": {"doctype": "Customer", "data": {}}}
		return [
			frappe._dict(role="user", content="add a customer", approval=None, tool_call_id=None),
			frappe._dict(
				role="assistant", content="", tool_calls=json.dumps([call]), approval=None, tool_call_id=None
			),
			frappe._dict(role="tool", tool_call_id="c1", content=None, approval="Pending", is_error=0),
		]

	def setUp(self):
		patcher = patch(
			"frappe_intelligence.intelligence.doctype.ai_conversation.ai_conversation.frappe.throw",
			side_effect=frappe.ValidationError,
		)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_approving_queues_the_change_with_its_call(self):
		doc = NS(messages=self.rows())
		AIConversation.decide(doc, "c1", True)
		[(row, call)] = AIConversation.approved_to_run(doc)
		self.assertEqual(
			(row.approval, call.name, call.arguments["doctype"]), ("Approved", "create_document", "Customer")
		)

	def test_rejecting_answers_the_call_for_the_model(self):
		doc = NS(messages=self.rows())
		AIConversation.decide(doc, "c1", False)
		self.assertEqual(doc.messages[2].content, REJECTED_RESULT)
		self.assertEqual(AIConversation.approved_to_run(doc), [])

	def test_a_change_can_be_decided_only_once(self):
		doc = NS(messages=self.rows())
		AIConversation.decide(doc, "c1", True)
		with self.assertRaises(frappe.ValidationError):
			AIConversation.decide(doc, "c1", True)

	def test_a_question_sent_as_a_file_is_named_after_it(self):
		file = {"file_url": "/files/a.pdf", "file_name": "invoice.pdf"}
		doc = NS(title=None, messages=[frappe._dict(role="user", content="", attachments=json.dumps([file]))])
		AIConversation.validate(doc)
		self.assertEqual(doc.title, "invoice.pdf")

	def test_files_are_read_once_per_question(self):
		file = {"file_url": "/files/a.pdf", "file_name": "a.pdf"}
		question = frappe._dict(role="user", attachments=json.dumps([file]))
		[call] = AIConversation.unread_attachments(NS(messages=[question]))
		self.assertEqual((call.name, call.arguments), ("read_document", file))
		answered = NS(messages=[question, frappe._dict(role="assistant")])
		self.assertEqual(AIConversation.unread_attachments(answered), [])

	def test_a_discarded_reading_tells_the_model(self):
		doc = NS(messages=self.review_rows())
		AIConversation.decide(doc, "r1", False)
		self.assertEqual(doc.messages[1].content, review.DISCARDED_RESULT)

	def test_moving_on_keeps_the_reading_marked_unchecked(self):
		doc = NS(messages=self.review_rows())
		doc.pending_proposals = lambda: AIConversation.pending_proposals(doc)
		AIConversation.reject_pending(doc)
		result = json.loads(doc.messages[1].content)
		self.assertEqual((result["text"], result["note"]), ("GP-8841", review.UNCONFIRMED_NOTE))

	@staticmethod
	def review_rows():
		return [
			frappe._dict(role="user", content="", approval=None, tool_call_id=None),
			frappe._dict(
				role="tool",
				tool_call_id="r1",
				content='{"text": "GP-8841"}',
				approval="Pending",
				preview='{"kind": "review"}',
			),
		]

	def test_a_new_message_rejects_what_is_still_waiting(self):
		doc = NS(messages=self.rows())
		doc.pending_proposals = lambda: AIConversation.pending_proposals(doc)
		AIConversation.reject_pending(doc)
		self.assertEqual((doc.messages[2].approval, doc.messages[2].content), ("Rejected", MOVED_ON_RESULT))
