"""Tutorial progress (the topics a user has done), over fakes; no site needed."""

from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import patch

import frappe

from frappe_intelligence.tutorial import progress


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
