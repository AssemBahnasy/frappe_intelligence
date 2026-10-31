"""Background runs: event stream, Stop flag and the job, over fakes; no site needed."""

from __future__ import annotations

from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

from frappe_intelligence.agent import runs
from frappe_intelligence.agent.loop import Step, TurnResult


class TestStream(TestCase):
	def setUp(self):
		patcher = patch.object(runs.frappe, "publish_realtime")
		self.publish = patcher.start()
		self.addCleanup(patcher.stop)

	def events(self):
		return [call.args[1] for call in self.publish.call_args_list]

	def test_every_event_carries_the_run_and_goes_to_the_owner(self):
		runs.Stream("ana@example.com", "conv-1", "run-1").step(
			Step("c1", "count_documents", "Counting", "running")
		)
		event, payload = self.publish.call_args.args
		self.assertEqual(event, runs.EVENT)
		self.assertEqual(self.publish.call_args.kwargs, {"user": "ana@example.com"})
		self.assertEqual(
			payload,
			{
				"run_id": "run-1",
				"conversation": "conv-1",
				"type": "step",
				"call_id": "c1",
				"tool": "count_documents",
				"label": "Counting",
				"status": "running",
			},
		)

	def test_text_is_batched(self):
		stream = runs.Stream("u", "c", "r")
		with patch.object(runs.time, "monotonic", return_value=stream.flushed_at):
			for delta in ("a", "b", "c"):
				stream.text(delta)
			self.assertEqual(self.events(), [])
			stream.text("x" * runs.TEXT_FLUSH_CHARS)
		self.assertEqual([e["text"] for e in self.events()], ["abc" + "x" * runs.TEXT_FLUSH_CHARS])

	def test_pending_text_goes_out_before_a_step_and_the_end(self):
		stream = runs.Stream("u", "c", "r")
		with patch.object(runs.time, "monotonic", return_value=stream.flushed_at):
			stream.text("Checking")
			stream.step(Step("c1", "t", "T", "running"))
			stream.text("Done")
			stream.done(TurnResult(reply="Done"))
		self.assertEqual([e["type"] for e in self.events()], ["text", "step", "text", "done"])
		self.assertEqual(self.events()[-1]["reply"], "Done")


class TestStopFlag(TestCase):
	def test_reads_redis_at_most_every_half_second_and_stays_stopped(self):
		flag = runs.StopFlag("r")
		with patch.object(runs.frappe, "cache") as cache, patch.object(runs.time, "monotonic") as clock:
			cache.get_value.return_value = None
			clock.return_value = 100.0
			self.assertFalse(flag())
			clock.return_value = 100.2
			self.assertFalse(flag())
			self.assertEqual(cache.get_value.call_count, 1)
			cache.get_value.return_value = 1
			clock.return_value = 100.6
			self.assertTrue(flag())
			cache.get_value.return_value = None
			clock.return_value = 200.0
			self.assertTrue(flag())
		cache.get_value.assert_called_with("fi_assistant_stop:r", use_local_cache=False)


class TestExecute(TestCase):
	def run_job(self, doc, run_turn):
		with (
			patch.object(runs.frappe, "get_doc", return_value=doc) as get_doc,
			patch.object(runs.frappe, "db", new=MagicMock()),
			patch.object(runs.frappe, "cache", new=MagicMock()),
			patch.object(runs.frappe, "log_error") as log_error,
			patch.object(runs.frappe, "publish_realtime") as publish,
			patch.object(runs, "_", side_effect=lambda text: text),
			patch.object(runs, "run_turn", side_effect=run_turn),
		):
			runs.execute("conv-1", "run-1")
		return publish, log_error, get_doc

	def test_answers_clears_the_run_and_ends_with_done(self):
		doc = MagicMock(active_run="run-1", owner="ana@example.com")
		publish, _, _ = self.run_job(doc, lambda conversation, hooks: TurnResult(reply="3 customers"))
		self.assertIsNone(doc.active_run)
		doc.save.assert_called()
		done = publish.call_args.args[1]
		self.assertEqual((done["type"], done["reply"]), ("done", "3 customers"))

	def test_unexpected_errors_are_logged_and_reported(self):
		doc = MagicMock(active_run="run-1", owner="ana@example.com")

		def crash(conversation, hooks):
			raise RuntimeError("bug")

		publish, log_error, _ = self.run_job(doc, crash)
		log_error.assert_called_once()
		doc.add_error.assert_called_once()
		self.assertIsNone(doc.active_run)
		self.assertTrue(publish.call_args.args[1]["error"])

	def test_a_replaced_run_does_nothing(self):
		doc = NS(active_run="run-2")
		publish, _, _ = self.run_job(doc, lambda *args: self.fail("should not run"))
		publish.assert_not_called()
