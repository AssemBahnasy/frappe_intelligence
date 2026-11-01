"""Short background jobs, voice input and optional packages, over fakes; no site needed."""

from __future__ import annotations

from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_intelligence.api import voice as voice_api
from frappe_intelligence.documents import voice
from frappe_intelligence.providers import ProviderError
from frappe_intelligence.utils import background, optional

USER = NS(user="a@example.com")


def throw(message, exc=frappe.ValidationError, *args, **kwargs):
	raise exc(message)


class TestBackground(TestCase):
	def run_job(self, **outcome):
		cache = MagicMock()
		with (
			patch.object(background.frappe, "get_attr", return_value=MagicMock(**outcome)) as get_attr,
			patch("frappe_intelligence.utils.background.frappe.cache", new=cache),
			patch("frappe_intelligence.utils.background.frappe.session", new=USER),
			patch.object(background.frappe, "publish_realtime") as publish,
			patch.object(background.frappe, "log_error") as log,
			patch.object(background, "_", side_effect=lambda text: text),
		):
			background.run("JOB1", "my.method", {"a": 1})
		get_attr.return_value.assert_called_once_with(a=1)
		[(key, result), kwargs] = cache.set_value.call_args
		self.assertEqual((key, kwargs), ("fi_job:a@example.com:JOB1", {"expires_in_sec": 600}))
		publish.assert_called_once_with("fi_job", {"job": "JOB1", **result}, user="a@example.com")
		return result, log

	def test_the_value_is_kept_for_the_user_and_sent_to_their_browser(self):
		result, log = self.run_job(return_value="Written.")
		self.assertEqual(result, {"value": "Written."})
		log.assert_not_called()

	def test_errors_meant_for_the_user_keep_their_message(self):
		for error in (
			ProviderError("offline"),
			optional.MissingPackage("no OCR"),
			frappe.ValidationError("bad"),
		):
			result, log = self.run_job(side_effect=error)
			self.assertEqual(result, {"error": str(error)})
			log.assert_not_called()

	def test_other_errors_are_logged_and_reported_in_general_terms(self):
		result, log = self.run_job(side_effect=KeyError("x"))
		self.assertEqual(result, {"error": "This could not be done. Please try again."})
		log.assert_called_once()

	def test_the_job_fits_frappe_enqueue(self):
		import inspect

		real_enqueue = frappe.enqueue
		with patch.object(background.frappe, "enqueue") as enqueue:
			job = background.start(
				"frappe_intelligence.writer.text.write", doctype="Customer", label="Details"
			)
		# Raises on a keyword frappe.enqueue takes itself, such as `method`.
		bound = inspect.signature(real_enqueue).bind(*enqueue.call_args.args, **enqueue.call_args.kwargs)
		self.assertEqual(bound.arguments["method"], "frappe_intelligence.utils.background.run")
		self.assertEqual(
			bound.arguments["kwargs"],
			{
				"job": job,
				"target": "frappe_intelligence.writer.text.write",
				"arguments": {"doctype": "Customer", "label": "Details"},
			},
		)

	def test_a_result_not_there_yet_is_pending(self):
		with (
			patch(
				"frappe_intelligence.utils.background.frappe.cache",
				new=MagicMock(**{"get_value.return_value": None}),
			),
			patch("frappe_intelligence.utils.background.frappe.session", new=USER),
		):
			self.assertEqual(background.result("JOB1"), {"pending": True})


class TestVoice(TestCase):
	def test_only_the_users_own_private_recording_is_accepted(self):
		with (
			patch.object(voice_api, "ensure_assistant_access"),
			patch.object(voice_api.optional, "installed", return_value=True),
			patch(
				"frappe_intelligence.api.voice.frappe.db", new=MagicMock(**{"get_value.return_value": None})
			) as db,
			patch("frappe_intelligence.api.voice.frappe.session", new=USER),
			patch.object(voice_api.frappe, "throw", side_effect=throw),
			patch.object(voice_api, "_", side_effect=lambda text: text),
		):
			with self.assertRaises(frappe.DoesNotExistError):
				voice_api.transcribe("/private/files/voice.webm")
		filters = db.get_value.call_args.args[1]
		self.assertEqual(
			filters,
			{
				"file_url": "/private/files/voice.webm",
				"owner": "a@example.com",
				"is_private": 1,
				"attached_to_doctype": ("is", "not set"),
			},
		)

	def test_a_file_that_is_not_audio_is_refused_even_when_it_is_the_users_own(self):
		with (
			patch.object(voice_api, "ensure_assistant_access"),
			patch.object(voice_api.optional, "installed", return_value=True),
			patch(
				"frappe_intelligence.api.voice.frappe.db",
				new=MagicMock(**{"get_value.return_value": "FILE-1"}),
			),
			patch("frappe_intelligence.api.voice.frappe.session", new=USER),
			patch.object(voice_api.frappe, "throw", side_effect=throw),
			patch.object(voice_api, "_", side_effect=lambda text: text),
			patch.object(voice_api.background, "start") as start,
		):
			with self.assertRaises(frappe.DoesNotExistError):
				voice_api.transcribe("/private/files/contract.pdf")
		start.assert_not_called()

	def test_without_the_package_voice_is_refused(self):
		with (
			patch.object(voice_api, "ensure_assistant_access"),
			patch.object(voice_api.optional, "installed", return_value=False),
			patch.object(voice_api.frappe, "throw", side_effect=throw),
			patch.object(voice_api, "_", side_effect=lambda text: text),
		):
			with self.assertRaises(frappe.ValidationError):
				voice_api.transcribe("/private/files/voice.webm")

	def test_the_recording_is_deleted_even_when_it_cannot_be_read(self):
		with (
			patch(
				"frappe_intelligence.documents.voice.frappe.db",
				new=MagicMock(**{"get_value.return_value": "/private/files/v.webm"}),
			),
			patch.object(voice, "resolve_file_path", return_value="/x/v.webm"),
			patch.object(voice, "language", return_value="ar"),
			patch.object(voice, "transcribe", side_effect=RuntimeError("bad audio")) as transcribe,
			patch.object(voice.frappe, "delete_doc") as delete,
		):
			with self.assertRaises(RuntimeError):
				voice.transcribe_recording("FILE-1")
		transcribe.assert_called_once_with("/x/v.webm", language="ar")
		delete.assert_called_once_with("File", "FILE-1", ignore_permissions=True)


class TestTranscriber(TestCase):
	def test_missing_settings_fall_back_to_cpu_defaults(self):
		from frappe_intelligence.documents import transcriber

		with (
			patch("frappe_intelligence.documents.transcriber.frappe.conf", new=frappe._dict()),
			patch.object(transcriber.optional, "require"),
			patch.object(transcriber, "_whisper_model", None),
			patch("faster_whisper.WhisperModel") as model,
			patch("frappe_intelligence.documents.transcriber.frappe.logger"),
		):
			transcriber._get_model()
		model.assert_called_once_with("medium", device="cpu", compute_type="int8")


class TestOptional(TestCase):
	def test_a_missing_package_says_which_feature_needs_it(self):
		with (
			patch.object(optional, "installed", return_value=False),
			patch.object(optional, "_", side_effect=lambda text: text),
		):
			with self.assertRaises(optional.MissingPackage) as raised:
				optional.require(optional.OCR)
		self.assertIn("OCR", str(raised.exception))
		self.assertIsInstance(raised.exception, ImportError)


class TestRequestsLimit(TestCase):
	def test_per_user_where_frappe_supports_it_and_per_address_before(self):
		from frappe_intelligence.utils import access

		def current(
			key=None, limit=5, seconds=86400, methods="ALL", ip_based=True, endpoint=None, user_based=False
		):
			return ("current", limit, seconds, ip_based, user_based)

		def older(key=None, limit=5, seconds=86400, methods="ALL", ip_based=True):
			return ("older", limit, seconds, ip_based)

		with patch.object(access, "rate_limit", current):
			self.assertEqual(access.requests_limit(), ("current", 20, 60, False, True))
		with patch.object(access, "rate_limit", older):
			self.assertEqual(access.requests_limit(), ("older", 20, 60, True))
