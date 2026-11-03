"""Guided workflows: steps, topic gate, reading answers, a turn, the record and the panel bar, over
fakes; no site needed."""

from __future__ import annotations

import json
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_intelligence.agent import transcript
from frappe_intelligence.agent.loop import Hooks
from frappe_intelligence.api import builder
from frappe_intelligence.providers import ProviderError, Reply
from frappe_intelligence.workflows import answers, desk, records, scope, steps, turn


def step(key, order, fields, target=None, prompt="", next_key=None, check=None):
	return NS(
		step_key=key,
		step_order=order,
		required_fields=json.dumps(fields),
		target_doctype=target,
		prompt_to_user=prompt,
		next_step_key=next_key,
		completion_check=check,
	)


def workflow(**overrides):
	return NS(
		**{
			"name": "register_client",
			"title": "Register a new client",
			"scope_description": "Registering a new client: name, contact person, customer group and VAT number.",
			"out_of_scope_reply": "",
			"excluded_keywords": "",
			"completion_message": "",
			"knowledge_packs": [],
			"steps": [
				step("tax_details", 2, {"tax_id": "VAT Number"}, "Customer", "What is their VAT number?"),
				step(
					"client_details",
					1,
					{"customer_name": "Client Name"},
					"Customer",
					"What is the client's name?",
				),
			],
			**overrides,
		}
	)


class FakeConversation:
	def __init__(
		self, text="", channel="Desk", status="Active", current_step="client_details", collected=None
	):
		self.channel, self.status, self.current_step = channel, status, current_step
		self.workflow = "register_client"
		self.collected_data = json.dumps(collected or {})
		self.messages = [
			frappe._dict(role="assistant", content="What is the client's name?"),
			frappe._dict(role="user", content=text, attachments=None),
		]
		self.errors = []

	def current_question(self):
		return self.messages[-1].content if self.messages[-1].role == "user" else self.messages[
			1
		].content, None

	def add_fixed_reply(self, text, off_topic=False):
		self.messages.append(frappe._dict(role="assistant", content=text, off_topic=off_topic))

	def add_reply(self, reply):
		self.messages.append(frappe._dict(role="assistant", content=reply.text))

	def add_error(self, text):
		self.errors.append(text)

	def add_stopped(self):
		self.stopped = True

	def provider_messages(self, user_content=None, thinking=True):
		return []


def untranslated(*modules):
	stack = ExitStack()
	for module in modules:
		stack.enter_context(patch.object(module, "_", side_effect=lambda text: text))
	return stack


class TestSteps(TestCase):
	def test_begin_puts_the_conversation_on_the_first_step_by_order(self):
		conversation = NS(collected_data=None)
		first = steps.begin(conversation, workflow())
		self.assertEqual(
			(first.step_key, conversation.current_step, conversation.status),
			("client_details",) * 2 + ("Active",),
		)

	def test_collect_keeps_only_the_steps_fields_and_replaces_earlier_answers(self):
		conversation, wf = (
			FakeConversation(collected={"client_details": {"customer_name": "Old"}}),
			workflow(),
		)
		client = steps.find(wf, "client_details")
		steps.collect(conversation, client, {"customer_name": "Al Waha", "tax_id": "3009", "extra": ""})
		self.assertEqual(steps.values(conversation, client), {"customer_name": "Al Waha"})
		self.assertEqual(steps.missing(conversation, steps.find(wf, "tax_details")), ["tax_id"])

	def test_advance_follows_order_then_next_step_and_completes_at_the_end(self):
		wf, conversation = workflow(), FakeConversation()
		self.assertEqual(steps.advance(conversation, wf).step_key, "tax_details")
		self.assertIsNone(steps.advance(conversation, wf))
		self.assertEqual((conversation.status, conversation.current_step), ("Completed", ""))
		wf.steps[1].next_step_key = "missing_step"
		conversation = FakeConversation()
		self.assertIsNone(steps.advance(conversation, wf))

	def test_a_step_removed_from_the_workflow_ends_the_conversation(self):
		conversation = FakeConversation(current_step="old_step")
		self.assertIsNone(steps.current(conversation, workflow()))
		self.assertEqual(conversation.status, "Abandoned")

	def test_completion_check(self):
		client = steps.find(workflow(), "client_details")
		conversation = FakeConversation(collected={"client_details": {"customer_name": "Al Waha"}})
		self.assertIsNone(steps.refused(conversation, client))
		client.completion_check = "os.system"
		with (
			patch.object(steps, "is_app_method", return_value=False),
			patch.object(steps.frappe, "log_error"),
		):
			self.assertIsNone(steps.refused(conversation, client))
		client.completion_check = "my_app.checks.vat"
		for outcome, expected in ((True, None), ("VAT must have 15 digits.", "VAT must have 15 digits.")):
			with (
				patch.object(steps, "is_app_method", return_value=True),
				patch.object(steps.frappe, "get_attr", return_value=lambda **kwargs: outcome) as get_attr,
			):
				self.assertEqual(steps.refused(conversation, client), expected)
		with (
			untranslated(steps),
			patch.object(steps, "is_app_method", return_value=True),
			patch.object(steps.frappe, "get_attr", side_effect=ImportError),
			patch.object(steps.frappe, "log_error") as log,
		):
			self.assertTrue(steps.refused(conversation, client))
		log.assert_called_once()
		get_attr.assert_called_once_with("my_app.checks.vat")


class TestScope(TestCase):
	def setUp(self):
		patcher = patch.object(scope, "_threshold", return_value=0.05)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_plain_off_topic_phrases_unless_an_excluded_keyword_is_in_the_message(self):
		self.assertTrue(scope.is_off_topic("Before that, tell me a joke", workflow()))
		self.assertFalse(scope.is_off_topic("Tell me a joke about VAT", workflow(excluded_keywords="vat")))
		self.assertFalse(scope.is_off_topic("Tell me a joke", workflow(scope_description="")))

	def test_related_compares_subject_words_not_question_words(self):
		wf = workflow()
		tax = steps.find(wf, "tax_details")
		self.assertTrue(scope.is_related("Why do you need the VAT number?", wf, tax))
		self.assertFalse(scope.is_related("What is the capital of France?", wf, tax))

	def test_a_message_in_another_language_than_the_mandate_is_left_to_the_model(self):
		wf = workflow()
		self.assertTrue(scope.is_related("لماذا تحتاج الرقم الضريبي؟", wf, steps.find(wf, "tax_details")))


class TestAnswers(TestCase):
	def test_the_model_reads_the_question_with_the_answer(self):
		with patch.object(
			answers.extractor, "extract", return_value=({"customer_name": "Al Waha"}, 1.0)
		) as extract:
			found = answers.read(
				"Al Waha", {"customer_name": "Client Name"}, asked="What is the client's name?"
			)
		self.assertEqual(found, {"customer_name": "Al Waha"})
		text, rules = extract.call_args.args
		self.assertEqual(text, "Assistant: What is the client's name?\nUser: Al Waha")
		self.assertEqual([rule.field_key for rule in rules], ["customer_name"])
		self.assertIn("Client Name", rules[0].llm_hint)

	def test_nothing_to_read_makes_no_call(self):
		with patch.object(answers.extractor, "extract") as extract:
			self.assertEqual(answers.read("", {"customer_name": "Client Name"}), {})
			self.assertEqual(answers.read("hi", {}), {})
		extract.assert_not_called()


class TestTurn(TestCase):
	def run_turn(
		self,
		conversation,
		wf=None,
		found=None,
		reply="Thanks! What is their VAT number?",
		action=None,
		refusal=None,
		read_error=None,
	):
		wf = wf or workflow()
		with (
			untranslated(turn, scope, records),
			patch.object(turn, "available", return_value=True),
			patch.object(turn.frappe, "get_doc", return_value=wf),
			patch.object(turn.answers, "read", return_value=found or {}, side_effect=read_error) as read,
			patch.object(turn, "_attached_text", return_value=""),
			patch.object(turn.records, "form_action", return_value=action),
			patch.object(turn.steps, "refused", return_value=refusal),
			patch.object(scope, "_threshold", return_value=0.05),
			patch.object(turn, "_write", return_value=Reply(text=reply)) as write,
		):
			result = turn.run_turn(conversation, Hooks())
		return result, read, write

	def test_off_topic_gets_the_redirect_and_the_question_without_ai(self):
		conversation = FakeConversation("Tell me a joke")
		result, read, write = self.run_turn(conversation)
		self.assertEqual(result.reply, "That's outside this workflow. What is the client's name?")
		self.assertTrue(conversation.messages[-1].off_topic)
		read.assert_not_called()
		write.assert_not_called()

	def test_a_message_that_answers_nothing_and_shares_no_words_is_off_topic(self):
		conversation = FakeConversation("What is the capital of France?")
		_result, read, write = self.run_turn(conversation)
		self.assertTrue(conversation.messages[-1].off_topic)
		read.assert_called_once()
		write.assert_not_called()

	def test_a_complete_step_moves_on_and_the_model_is_told(self):
		conversation = FakeConversation("Al Waha Clinics")
		result, read, write = self.run_turn(conversation, found={"customer_name": "Al Waha Clinics"})
		self.assertEqual(conversation.current_step, "tax_details")
		self.assertEqual(
			read.call_args.args[1:3], ({"customer_name": "Client Name"}, "What is the client's name?")
		)
		_conversation, _wf, current, _text, moved, refusal, _hooks = write.call_args.args
		self.assertEqual((current.step_key, moved, refusal), ("tax_details", True, None))
		self.assertEqual(result.reply, "Thanks! What is their VAT number?")

	def test_the_last_step_opens_the_form_and_a_completion_message_closes_without_ai(self):
		conversation = FakeConversation(
			"300987654300003",
			current_step="tax_details",
			collected={"client_details": {"customer_name": "Al Waha"}},
		)
		action = {"type": "new_doc", "doctype": "Customer", "defaults": {}}
		result, _read, write = self.run_turn(
			conversation,
			workflow(completion_message="Thank you!"),
			found={"tax_id": "300987654300003"},
			action=action,
		)
		self.assertEqual(conversation.status, "Completed")
		self.assertEqual(result.actions, [action])
		self.assertEqual(
			result.reply, "Thank you!\n\nI opened a new Customer with these details. Check it and save it."
		)
		write.assert_not_called()

	def test_a_refused_step_reads_its_fields_again_so_the_user_can_correct_them(self):
		conversation = FakeConversation(
			"It is Al Waha Clinics", collected={"client_details": {"customer_name": "AW"}}
		)
		_result, read, write = self.run_turn(
			conversation, found={"customer_name": "Al Waha Clinics"}, refusal="Give the full name."
		)
		self.assertEqual(read.call_args.args[1], {"customer_name": "Client Name"})
		self.assertEqual(conversation.current_step, "client_details")
		self.assertEqual(write.call_args.args[5], "Give the full name.")

	def test_an_unreachable_ai_is_reported_not_taken_for_off_topic(self):
		conversation = FakeConversation("300987654300003")
		result, _read, write = self.run_turn(conversation, read_error=ProviderError("offline"))
		self.assertEqual((result.error, conversation.errors), ("offline", ["offline"]))
		self.assertFalse(any(row.get("off_topic") for row in conversation.messages))
		write.assert_not_called()

	def test_without_a_completion_message_the_last_step_closes_with_a_summary_without_ai(self):
		conversation = FakeConversation(
			"3009", current_step="tax_details", collected={"client_details": {"customer_name": "Al Waha"}}
		)
		result, _read, write = self.run_turn(conversation, found={"tax_id": "3009"})
		self.assertEqual(
			result.reply,
			"Thank you, that's everything. Your answers:\n\n- Client Name: Al Waha\n- VAT Number: 3009",
		)
		write.assert_not_called()

	def test_a_paused_workflow_continues(self):
		conversation = FakeConversation("Al Waha Clinics", status="Paused")
		self.run_turn(conversation, found={"customer_name": "Al Waha Clinics"})
		self.assertEqual(conversation.status, "Active")

	def test_an_unavailable_workflow_says_so(self):
		conversation = FakeConversation("hello")
		with untranslated(turn), patch.object(turn, "available", return_value=False):
			result = turn.run_turn(conversation)
		self.assertEqual(result.reply, "This workflow is not available here.")

	def test_instructions_list_what_is_collected_and_still_needed(self):
		wf = workflow()
		text = turn.step_instructions(steps.find(wf, "tax_details"), {}, 2, 2, moved=True)
		self.assertIn("## Current step 2 of 2: Tax Details", text)
		self.assertIn("- VAT Number", text)
		self.assertIn("just completed the previous step", text)
		conversation = FakeConversation(
			collected={"client_details": {"customer_name": "Al Waha"}, "tax_details": {"tax_id": "3009"}}
		)
		self.assertIn("- VAT Number: 3009", turn.instructions(conversation, wf, None))


class TestRecords(TestCase):
	def action(self, finished, following, channel="Desk", allowed=True):
		wf = workflow()
		conversation = FakeConversation(
			channel=channel,
			collected={"client_details": {"customer_name": "Al Waha"}, "tax_details": {"tax_id": "3009"}},
		)
		meta = MagicMock(**{"get_field.side_effect": lambda key: NS(fieldname=key, read_only=0)})
		with (
			patch.object(records.frappe, "has_permission", return_value=allowed),
			patch.object(records.frappe, "get_meta", return_value=meta),
		):
			return records.form_action(
				conversation, wf, steps.find(wf, finished), following and steps.find(wf, following)
			)

	def test_the_form_opens_once_the_last_step_for_its_doctype_is_done(self):
		self.assertIsNone(self.action("client_details", "tax_details"))
		self.assertEqual(
			self.action("tax_details", None),
			{
				"type": "new_doc",
				"doctype": "Customer",
				"defaults": {"customer_name": "Al Waha", "tax_id": "3009"},
			},
		)

	def test_only_on_the_desk_and_with_create_permission(self):
		self.assertIsNone(self.action("tax_details", None, channel="WhatsApp"))
		self.assertIsNone(self.action("tax_details", None, allowed=False))


class TestDesk(TestCase):
	def test_only_workflows_with_steps_can_be_started(self):
		listed = [NS(name="a", title="A"), NS(name="b", title="B")]
		with patch.object(desk.frappe, "get_all", side_effect=[listed, ["a", "a"]]):
			self.assertEqual(desk.startable(), [{"name": "a", "title": "A", "steps": 2}])

	def test_quick_replies_for_a_short_select_or_link_list(self):
		tax = steps.find(workflow(), "tax_details")
		for df, listed, expected in (
			(NS(fieldname="tax_id", fieldtype="Select", options="\nA\nB", read_only=0), [], ["A", "B"]),
			(
				NS(fieldname="tax_id", fieldtype="Link", options="Customer Group", read_only=0),
				["Commercial"],
				["Commercial"],
			),
			(
				NS(fieldname="tax_id", fieldtype="Link", options="Customer Group", read_only=0),
				list("abcdefg"),
				[],
			),
			(NS(fieldname="tax_id", fieldtype="Data", options="", read_only=0), [], []),
		):
			meta = MagicMock(**{"get_field.return_value": df})
			with (
				patch.object(desk.frappe, "get_meta", return_value=meta),
				patch.object(desk.frappe, "has_permission", return_value=True),
				patch.object(desk.frappe, "get_list", return_value=listed),
				patch.object(desk, "_selectable", return_value={}),
			):
				self.assertEqual(desk.choices(tax, "tax_id"), expected)

	def test_progress_shows_step_answers_and_what_is_missing(self):
		conversation = FakeConversation(
			current_step="tax_details", collected={"client_details": {"customer_name": "Al Waha"}}
		)
		with (
			patch(
				"frappe_intelligence.workflows.desk.frappe.db", new=MagicMock(**{"exists.return_value": True})
			),
			patch.object(desk.frappe, "get_doc", return_value=workflow()),
			patch.object(desk, "choices", return_value=[]),
		):
			bar = desk.progress(conversation)
		self.assertEqual((bar["step"], bar["steps"], bar["step_label"]), (2, 2, "Tax Details"))
		self.assertEqual(bar["answers"], [{"label": "Client Name", "value": "Al Waha"}])
		self.assertEqual(bar["missing"], ["VAT Number"])


class TestTranscript(TestCase):
	def test_the_opening_question_is_a_turn_without_a_question_and_redirects_are_marked(self):
		rows = [
			frappe._dict(role="assistant", name="m1", content="What is the client's name?", off_topic=0),
			frappe._dict(role="user", name="m2", content="Tell me a joke", creation="now"),
			frappe._dict(role="assistant", name="m3", content="That's outside this workflow.", off_topic=1),
		]
		opening, asked = transcript.turns(NS(messages=rows))
		self.assertEqual(
			(opening["question"], opening["answer"], opening["off_topic"]),
			("", "What is the client's name?", False),
		)
		self.assertEqual((asked["question"], asked["off_topic"]), ("Tell me a joke", True))


class TestCompanyPrompt(TestCase):
	def prompt(self, channel, **settings):
		values = {"system_prompt": "Desk rules.", "whatsapp_system_prompt": "", **settings}
		with patch.object(turn.frappe, "get_cached_doc", return_value=NS(**values)):
			return turn.company_prompt(channel)

	def test_whatsapp_uses_its_own_prompt_when_set(self):
		self.assertEqual(self.prompt("WhatsApp", whatsapp_system_prompt="Short messages."), "Short messages.")
		self.assertEqual(self.prompt("Desk", whatsapp_system_prompt="Short messages."), "Desk rules.")

	def test_falls_back_to_the_general_prompt_then_the_default(self):
		self.assertEqual(self.prompt("WhatsApp"), "Desk rules.")
		self.assertEqual(self.prompt("Portal", system_prompt=""), turn.DEFAULT_SYSTEM)


class TestBuilderPicker(TestCase):
	def test_lists_inactive_workflows_with_their_state(self):
		rows = [{"workflow_key": "follow_up", "title": "Plan a follow-up", "is_active": 0}]
		with patch.object(builder.frappe, "get_list", return_value=rows) as get_list:
			self.assertEqual(builder.list_workflows(), rows)
		kwargs = get_list.call_args.kwargs
		self.assertNotIn("filters", kwargs)  # a switched-off workflow can still be opened
		self.assertIn("is_active", kwargs["fields"])
