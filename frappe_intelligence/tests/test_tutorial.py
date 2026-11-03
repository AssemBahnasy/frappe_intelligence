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

	def test_failure_keeps_finished_timings_and_removes_the_user(self):
		with (
			patch.object(recorder.frappe, "conf", frappe._dict(developer_mode=1)),
			patch.object(recorder, "make_user"),
			patch.object(recorder, "session", return_value="sid"),
			patch.object(recorder.frappe.utils, "get_url", return_value="http://site"),
			patch.object(recorder.frappe.db, "set_value"),
			patch.object(recorder.frappe.db, "commit"),
			patch.object(recorder.frappe, "clear_cache"),
			patch.object(recorder.frappe, "throw", side_effect=throw),
			patch.object(
				recorder, "run_recorder", side_effect=[({"ask": {"duration": 20}}, False), ({}, True)]
			),
			patch.object(recorder, "save_timings") as save_timings,
			patch.object(recorder, "remove_user") as remove_user,
		):
			with self.assertRaises(frappe.ValidationError):
				recorder.record(["ask"], ["en", "ar"], "Sara")
		# What was recorded before the failure keeps its timings, saved once.
		save_timings.assert_called_once_with({"en": {"ask": {"duration": 20}}, "ar": {}})
		remove_user.assert_called_once()

	def test_timings_merge_by_topic_and_language(self):
		with tempfile.TemporaryDirectory() as folder:
			for lang, topic in (("en", "ask"), ("en", "voice"), ("ar", "ask")):
				os.makedirs(os.path.join(folder, lang), exist_ok=True)
				with open(os.path.join(folder, lang, f"{topic}.mp4"), "wb") as f:
					f.write(f"{lang} {topic}".encode())
			path = os.path.join(folder, "videos.json")
			with patch.object(recorder, "TIMINGS", path), patch.object(recorder, "VIDEOS", folder):
				recorder.save_timings({"en": {"ask": {"duration": 20, "steps": [1, 7]}}})
				recorder.save_timings(
					{"en": {"voice": {"duration": 9}}, "ar": {"ask": {"duration": 21, "steps": [1, 8]}}}
				)
			with open(path) as f:
				timings = json.load(f)
		versions = {lang: timing.pop("version") for lang, timing in timings["ask"].items()}
		timings["voice"]["en"].pop("version")
		self.assertEqual(
			timings,
			{
				"ask": {"ar": {"duration": 21, "steps": [1, 8]}, "en": {"duration": 20, "steps": [1, 7]}},
				"voice": {"en": {"duration": 9}},
			},
		)
		# A different file gets a different version, so browsers fetch it again.
		self.assertNotEqual(versions["en"], versions["ar"])


class TestSampleData(TestCase):
	def run_create(self, existing):
		workflow = frappe._dict(name="follow_up", title="Plan a follow-up")
		workflow.steps = [frappe._dict(prompt_to_user="What needs to be done?")]

		def get_doc(doc, name=None):
			return workflow if doc == "AI Workflow" else MagicMock()

		# How each DocType names its records (autoname "field:...").
		names = {
			"AI Knowledge Pack": "pack_name",
			"AI Document Template": "document_type_key",
			"AI Workflow": "workflow_key",
		}

		def meta(doctype):
			return frappe._dict(autoname=f"field:{names[doctype]}")

		with (
			patch.object(sample_data.frappe, "conf", frappe._dict(developer_mode=1)),
			patch.object(sample_data.frappe.defaults, "get_global_default", return_value="Demo Co"),
			patch.object(sample_data.frappe.db, "exists", side_effect=lambda doctype, name: existing),
			patch.object(sample_data.frappe.db, "commit"),
			patch.object(sample_data, "today", return_value="2026-11-03"),
			patch.object(sample_data.frappe, "get_meta", side_effect=meta),
			patch.object(sample_data.frappe, "get_doc", side_effect=get_doc) as calls,
		):
			sample_data.create()
		return [call.args[0]["doctype"] for call in calls.call_args_list if isinstance(call.args[0], dict)]

	def test_creates_every_record(self):
		with open(sample_data.DATA) as f:
			data = json.load(f)
		created = self.run_create(existing=False)
		self.assertEqual(created.count("Customer"), len(data["customers"]))
		self.assertEqual(created.count("Supplier"), len(data["suppliers"]))
		self.assertEqual(created.count("Item"), len(data["items"]))
		self.assertEqual(created.count("Sales Invoice"), len(data["sales_invoices"]))
		for doctype in {d["doctype"] for d in data["documents"]}:
			expected = sum(d["doctype"] == doctype for d in data["documents"])
			self.assertEqual(created.count(doctype), expected, doctype)
		sessions = sum(
			sum(s.get(status, 0) for status in ("Completed", "Active", "Abandoned"))
			for s in data["workflow_sessions"]
		)
		self.assertEqual(created.count("AI Conversation"), sessions)

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
