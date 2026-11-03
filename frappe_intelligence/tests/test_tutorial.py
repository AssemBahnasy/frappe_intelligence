"""Tutorial progress, the demo video recorder and its sample data, over fakes; no site needed."""

from __future__ import annotations

import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_intelligence.tutorial import progress, recorder, sample_data


def throw(message, exc=frappe.ValidationError, *args, **kwargs):
	raise exc(message)


class TestProgress(TestCase):
	def run_set_done(self, stored, topic, done):
		with (
			patch.object(progress.frappe.defaults, "get_user_default", return_value=stored),
			patch.object(progress.frappe.defaults, "set_user_default") as save,
			patch.object(progress.frappe, "throw", side_effect=throw),
			patch.object(progress, "_", side_effect=lambda text: text),
		):
			result = progress.set_done(topic, done)
		return result, save

	def test_marks_done_once(self):
		result, save = self.run_set_done(json.dumps(["ask"]), "ask", True)
		self.assertEqual(result, ["ask"])
		save.assert_called_once_with(progress.DONE_KEY, json.dumps(["ask"]), None)

	def test_marks_not_done(self):
		result, _save = self.run_set_done(json.dumps(["ask", "voice"]), "ask", False)
		self.assertEqual(result, ["voice"])

	def test_unreadable_value_starts_fresh(self):
		for stored in ("not json", json.dumps({"ask": 1}), None):
			result, _save = self.run_set_done(stored, "voice", True)
			self.assertEqual(result, ["voice"])

	def test_refuses_what_is_not_a_topic_key(self):
		for topic in ("", "Ask", "a" * 41, "../x", None):
			with self.assertRaises(frappe.ValidationError):
				self.run_set_done("[]", topic, True)

	def test_keeps_the_latest_topics(self):
		stored = json.dumps([f"t{i}" for i in range(progress.MAX_TOPICS)])
		result, _save = self.run_set_done(stored, "new", True)
		self.assertEqual((len(result), result[0], result[-1]), (progress.MAX_TOPICS, "t1", "new"))


class TestRecorder(TestCase):
	def test_only_on_a_development_site(self):
		with (
			patch.object(recorder.frappe, "conf", frappe._dict(developer_mode=0)),
			patch.object(recorder.frappe, "throw", side_effect=throw),
			patch.object(recorder, "make_user") as make_user,
		):
			with self.assertRaises(frappe.ValidationError):
				recorder.record([], ["en"], "Sara")
		make_user.assert_not_called()

	def test_user_removed_when_recording_fails(self):
		with (
			patch.object(recorder.frappe, "conf", frappe._dict(developer_mode=1)),
			patch.object(recorder, "make_user"),
			patch.object(recorder, "session", return_value="sid"),
			patch.object(recorder.frappe.utils, "get_url", return_value="http://site"),
			patch.object(recorder.frappe.db, "set_value"),
			patch.object(recorder.frappe.db, "commit"),
			patch.object(recorder.frappe, "clear_cache"),
			patch.object(recorder, "run_recorder", side_effect=RuntimeError("scene failed")),
			patch.object(recorder, "remove_user") as remove_user,
		):
			with self.assertRaises(RuntimeError):
				recorder.record(["ask"], ["en"], "Sara")
		remove_user.assert_called_once()

	def test_timings_merge_by_topic_and_language(self):
		with tempfile.TemporaryDirectory() as folder:
			path = os.path.join(folder, "videos.json")
			with patch.object(recorder, "TIMINGS", path):
				recorder.save_timings(
					"en", {"ask": {"duration": 20, "steps": [1, 7]}, "voice": {"duration": 9}}
				)
				recorder.save_timings("ar", {"ask": {"duration": 21, "steps": [1, 8]}})
			with open(path) as f:
				timings = json.load(f)
		self.assertEqual(
			timings,
			{
				"ask": {"ar": {"duration": 21, "steps": [1, 8]}, "en": {"duration": 20, "steps": [1, 7]}},
				"voice": {"en": {"duration": 9}},
			},
		)


class TestSampleData(TestCase):
	def run_create(self, existing):
		with (
			patch.object(sample_data.frappe, "conf", frappe._dict(developer_mode=1)),
			patch.object(sample_data.frappe.defaults, "get_global_default", return_value="Demo Co"),
			patch.object(sample_data.frappe.db, "exists", side_effect=lambda doctype, name: existing),
			patch.object(sample_data.frappe.db, "commit"),
			patch.object(sample_data, "today", return_value="2026-11-03"),
			patch.object(sample_data.frappe, "get_doc", return_value=MagicMock()) as get_doc,
		):
			sample_data.create()
		return [call.args[0]["doctype"] for call in get_doc.call_args_list]

	def test_creates_every_record(self):
		with open(sample_data.DATA) as f:
			data = json.load(f)
		created = self.run_create(existing=False)
		self.assertEqual(created.count("Customer"), len(data["customers"]))
		self.assertEqual(created.count("Item"), len(data["items"]))
		self.assertEqual(created.count("Sales Invoice"), len(data["sales_invoices"]))

	def test_adds_nothing_the_second_time(self):
		self.assertEqual(self.run_create(existing=True), [])

	def test_only_on_a_development_site(self):
		with (
			patch.object(sample_data.frappe, "conf", frappe._dict(developer_mode=0)),
			patch.object(sample_data.frappe, "throw", side_effect=throw),
			patch.object(sample_data.frappe, "get_doc") as get_doc,
		):
			with self.assertRaises(frappe.ValidationError):
				sample_data.create()
		get_doc.assert_not_called()
