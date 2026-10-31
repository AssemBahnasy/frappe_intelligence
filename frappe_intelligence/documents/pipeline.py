"""
The document pipeline for the portal, WhatsApp and integrations (`api.documents`); the assistant
panel reads files through documents/review.py instead.

Flow
----
1.  Read the file (OCR via EasyOCR or text extraction).
2.  Classify the document by matching detection keywords against the
    raw text (or against the optional *target_doctype* hint).
3.  Select the matching AI Document Template.
4.  Extract with regex rules, the configured AI provider, or both.
5.  Persist an AI Processing Log and return the extracted payload.

Readers, template matching and extraction are the modules beside this one.

Async processing
----------------
``process_document_background`` is enqueued by ``api.process_document``
so the HTTP request returns immediately.  The background job runs the
full pipeline and pushes the result to the browser via
``frappe.publish_realtime("ai_processing_complete", ...)``.
"""

from __future__ import annotations

import traceback
from typing import Any

import frappe

from frappe_intelligence.documents import review, templates
from frappe_intelligence.utils.callables import is_app_method


class AIEngine:
	"""Orchestrates the full document-intelligence pipeline."""

	# ------------------------------------------------------------------
	# Public API
	# ------------------------------------------------------------------

	def process(self, file_url: str, target_doctype: str | None = None) -> dict[str, Any]:
		"""
		Create a new Processing Log and run the full pipeline synchronously.

		Kept for internal callers (e.g. tests, bench console).
		HTTP requests should use the background path via api.process_document.
		"""
		log = self._create_log(file_url)
		return self._run_pipeline(log, file_url, target_doctype)

	def process_from_log(
		self, log_name: str, file_url: str, target_doctype: str | None = None
	) -> dict[str, Any]:
		"""
		Run the pipeline on an already-created Processing Log.

		Used by ``process_document_background`` so the background worker
		can pick up a log that was committed before the job was enqueued.
		"""
		log = frappe.get_doc("AI Processing Log", log_name)
		return self._run_pipeline(log, file_url, target_doctype)

	# ------------------------------------------------------------------
	# Core pipeline
	# ------------------------------------------------------------------

	def _run_pipeline(self, log, file_url: str, target_doctype: str | None) -> dict[str, Any]:
		"""
		Run OCR → classify → extract → persist and return the result dict.

		Parameters
		----------
		log:
		    An AI Processing Log doc (already inserted and committed).
		file_url:
		    Frappe file URL of the document to process.
		target_doctype:
		    Optional ``document_type_key`` hint; skips auto-classification.

		Returns
		-------
		dict with keys: status, document_type_key, extracted_data,
		                confidence_score, log_name.
		"""
		try:
			raw_text = self._read_file(file_url)
			log.raw_text = raw_text
			log.processing_status = "Processing"
			log.save(ignore_permissions=True)

			template = templates.match(raw_text, target_doctype)
			if not template:
				raise ValueError(
					f"No AI Document Template matched the document. (target_doctype={target_doctype!r})"
				)

			log.document_template = template.name
			extracted, confidence = templates.extract(raw_text, template)

			log.extracted_data = frappe.as_json(extracted)
			log.confidence_score = confidence
			log.processing_status = "Completed"
			log.save(ignore_permissions=True)

			return {
				"status": "success",
				"document_type_key": template.document_type_key,
				"extracted_data": extracted,
				"confidence_score": confidence,
				"log_name": log.name,
			}

		except Exception as exc:
			tb = traceback.format_exc()
			frappe.log_error(title="AI Processing failed", message=tb)
			log.processing_status = "Failed"
			log.error_message = f"{type(exc).__name__}: {exc}"
			log.save(ignore_permissions=True)
			return {
				"status": "failed",
				"document_type_key": None,
				"extracted_data": {},
				"confidence_score": 0.0,
				"log_name": log.name,
			}

	# ------------------------------------------------------------------
	# Step helpers
	# ------------------------------------------------------------------

	def _create_log(self, file_url: str):
		log = frappe.new_doc("AI Processing Log")
		log.file_url = file_url
		log.processing_status = "Pending"
		log.insert(ignore_permissions=True)
		frappe.db.commit()
		return log

	def _read_file(self, file_url: str) -> str:
		from frappe_intelligence.documents.reader import read_file_text

		return read_file_text(file_url)


# ===========================================================================
# Background job entry-point
# (enqueued by api.process_document — runs in a long-queue worker)
# ===========================================================================


def process_document_background(
	log_name: str,
	file_url: str,
	target_doctype: str | None,
	session_user: str,
) -> None:
	"""
	Background worker: run the full pipeline on an existing Processing Log
	and push the result to the triggering user via realtime.

	Enqueued by ``frappe_intelligence.api.documents.process_document``.
	The HTTP request creates the log and returns immediately; this function
	does the heavy lifting (OCR + LLM) asynchronously.
	"""
	try:
		result = AIEngine().process_from_log(log_name, file_url, target_doctype)

		threshold = review.confidence_threshold()
		needs_review = result.get("status") == "success" and result.get("confidence_score", 0.0) < threshold
		result["needs_review"] = needs_review

		if not needs_review:
			fire_post_processors(result.get("document_type_key"), result, None, None)

	except Exception:
		frappe.log_error(title="AI Background Processing failed", message=frappe.get_traceback())
		result = {
			"status": "failed",
			"document_type_key": None,
			"extracted_data": {},
			"confidence_score": 0.0,
			"log_name": log_name,
			"needs_review": False,
		}

	frappe.publish_realtime("ai_processing_complete", result, user=session_user)


# ===========================================================================
# Post-extraction pipeline helpers
# ===========================================================================


def fire_post_processors(
	document_type_key: str | None,
	extraction_result: dict,
	doctype: str | None,
	docname: str | None,
) -> None:
	"""
	Enqueue all active AI Post Processors for *document_type_key*.

	Only callbacks whose top-level package is an installed Frappe app
	are accepted; others are skipped and logged.
	"""
	if not document_type_key:
		return
	for method in frappe.get_all(
		"AI Post Processor",
		filters={"document_type_key": document_type_key, "is_active": 1},
		pluck="callback_method",
	):
		if not is_app_method(method):
			frappe.log_error(
				title=f"AI Post-Processor blocked: unsafe callback '{method}'",
				message=(
					"The callback_method must be a dotted Python path whose "
					"top-level package is an installed Frappe app. "
					f"Received: {method!r}"
				),
			)
			continue
		try:
			frappe.enqueue(
				method,
				queue="default",
				enqueue_after_commit=True,
				extraction_result=extraction_result,
				doctype=doctype,
				docname=docname,
			)
		except Exception:
			frappe.log_error(
				title=f"AI Post-Processor enqueue failed: {method}",
				message=frappe.get_traceback(),
			)


def link_log_to_record(
	log_name: str,
	doctype: str,
	docname: str,
	document_type_key: str | None,
) -> None:
	"""
	Update an AI Processing Log with the Frappe record it was triggered from.

	Best-effort: failures are logged but never surfaced to the caller.
	"""
	try:
		frappe.db.set_value(
			"AI Processing Log",
			log_name,
			{
				"linked_doctype": doctype,
				"linked_docname": docname,
				"document_type_key": document_type_key or "",
			},
			update_modified=False,
		)
	except Exception:
		frappe.log_error(
			title="AI Log link failed",
			message=frappe.get_traceback(),
		)
