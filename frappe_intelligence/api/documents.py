"""Document reading endpoints: upload, processing status, templates and review."""

from __future__ import annotations

import json as _json

import frappe

from frappe_intelligence.documents import review
from frappe_intelligence.engine.orchestrator import fire_post_processors, link_log_to_record
from frappe_intelligence.utils.access import ensure_assistant_access, limit_requests
from frappe_intelligence.utils.file_utils import validate_file_access


def ensure_record_access(doctype: str | None, docname: str | None) -> None:
	"""Post-processors and record links write to the record, so the user must be able to."""
	if doctype and docname:
		frappe.has_permission(doctype, "write", docname, throw=True)


def process_widget_file(
	file_url: str, doctype: str | None, docname: str | None, workflow_key: str | None
) -> dict:
	"""Read a file uploaded in the widget synchronously and link the result to the open record."""
	validate_file_access(file_url)
	ensure_record_access(doctype, docname)

	from frappe_intelligence.engine.orchestrator import AIEngine

	result = AIEngine().process(file_url=file_url)
	if doctype and docname and result.get("log_name"):
		link_log_to_record(result["log_name"], doctype, docname, result.get("document_type_key"))

	result["needs_review"] = result.get("status") == "success" and result.get(
		"confidence_score", 0.0
	) < review.confidence_threshold(workflow_key)
	if not result["needs_review"]:
		fire_post_processors(result.get("document_type_key"), result, doctype, docname)

	frappe.publish_realtime(
		"ai_processing_update", {"message": "Extraction complete!"}, user=frappe.session.user
	)
	return result


def _assert_log_access(log_name: str) -> None:
	"""
	Raise PermissionError if the current user is neither the owner of the
	AI Processing Log nor a System Manager.

	Used by confirm_extraction and submit_correction.  This ownership-based
	check is intentional: the AI Processing Log DocType carries no role
	permissions (it is created internally with ignore_permissions=True), so
	Frappe's standard has_permission() always returns False for non-admins.
	Instead we enforce that only the session that triggered the processing
	can act on its result.
	"""
	owner = frappe.db.get_value("AI Processing Log", log_name, "owner")
	if owner is None:
		frappe.throw(
			frappe._("Processing log not found: {0}").format(log_name),
			frappe.DoesNotExistError,
		)
	if owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(
			frappe._("You do not have permission to access this processing log."),
			frappe.PermissionError,
		)


@frappe.whitelist()
@limit_requests
def process_document(file_url: str, target_doctype: str | None = None) -> dict:
	"""
	Enqueue document processing and return immediately.

	The heavy work (OCR + LLM extraction) runs in a background long-queue
	worker.  When complete, the result is pushed to the browser via the
	``ai_processing_complete`` realtime event.

	Parameters
	----------
	file_url:
	    Frappe file URL (e.g. ``/files/national_address.jpg`` or
	    ``/private/files/cr_scan.pdf``).
	target_doctype:
	    Optional ``document_type_key`` of the expected AI Document Template.
	    Pass ``None`` for automatic classification.

	Returns
	-------
	``{"status": "queued", "log_name": str}``
	"""
	ensure_assistant_access()
	validate_file_access(file_url)

	from frappe_intelligence.engine.orchestrator import AIEngine

	log = AIEngine()._create_log(file_url)

	frappe.enqueue(
		"frappe_intelligence.engine.orchestrator.process_document_background",
		queue="long",
		timeout=600,
		log_name=log.name,
		file_url=file_url,
		target_doctype=target_doctype,
		session_user=frappe.session.user,
	)

	return {"status": "queued", "log_name": log.name}


@frappe.whitelist()
def get_log_status(log_name: str) -> dict:
	"""
	Return the current status of an AI Processing Log.

	Used by the widget as a polling fallback when the socket.io realtime
	event does not arrive (dev proxies, VPN, etc.).

	Returns
	-------
	``{"status": "Pending"|"Processing"|"Completed"|"Failed", "result": dict|None}``
	The ``result`` key mirrors the shape of the ``ai_processing_complete``
	realtime payload so the widget can call ``_handleProcessingResult`` directly.
	"""
	_assert_log_access(log_name)

	log = frappe.get_doc("AI Processing Log", log_name)

	if log.processing_status not in ("Completed", "Failed"):
		return {"status": log.processing_status, "result": None}

	log_session = frappe.db.get_value("AI Processing Log", log_name, "session")
	wf_key = frappe.db.get_value("AI Conversation", log_session, "workflow") if log_session else None
	threshold = review.confidence_threshold(wf_key)
	confidence = float(log.confidence_score or 0.0)
	needs_review = log.processing_status == "Completed" and confidence < threshold

	result = {
		"status": "success" if log.processing_status == "Completed" else "failed",
		"document_type_key": log.document_type_key or None,
		"extracted_data": frappe.parse_json(log.extracted_data or "{}"),
		"confidence_score": confidence,
		"log_name": log_name,
		"needs_review": needs_review,
	}
	return {"status": log.processing_status, "result": result}


@frappe.whitelist()
def list_templates() -> list[dict]:
	"""Return all active AI Document Templates (name, key, model preference)."""
	return frappe.get_all(
		"AI Document Template",
		filters={"is_active": 1},
		fields=["name", "document_name", "document_type_key", "model_preference"],
		order_by="document_name asc",
	)


@frappe.whitelist()
def submit_correction(log_name: str, corrected_extraction: dict | str) -> dict:
	"""
	Submit a user correction for a processed document.

	Creates an **AI Training Pair** linked to *log_name* so patterns can be
	improved over time.  Only the log owner or a System Manager may submit.

	Returns
	-------
	``{"training_pair": "<new AI Training Pair name>"}``
	"""
	_assert_log_access(log_name)

	if isinstance(corrected_extraction, str):
		corrected_extraction = _json.loads(corrected_extraction)

	log = frappe.get_doc("AI Processing Log", log_name)
	pair = frappe.new_doc("AI Training Pair")
	pair.document_template = log.document_template
	pair.processing_log = log_name
	pair.session = log.session if log.session else None
	pair.original_extraction = log.extracted_data
	pair.corrected_extraction = frappe.as_json(corrected_extraction)
	pair.correction_source = frappe.session.user
	pair.insert(ignore_permissions=True)
	return {"training_pair": pair.name}


@frappe.whitelist()
def register_post_processor(
	document_type_key: str,
	callback_method: str,
	description: str | None = None,
) -> dict:
	"""
	Register a Python callable to be enqueued after a successful extraction.

	Returns
	-------
	``{"name": "<new AI Post Processor doc name>"}``
	"""
	frappe.only_for("System Manager")
	doc = frappe.new_doc("AI Post Processor")
	doc.document_type_key = document_type_key
	doc.callback_method = callback_method
	doc.description = description or ""
	doc.is_active = 1
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def get_required_documents(doctype: str, docname: str) -> dict:
	"""
	Return present/missing required AI document types for a Frappe record.

	Used by the widget's proactive bubble and Smart Checklist.

	Returns
	-------
	``{"present": [...], "missing": [...]}``
	"""
	if not frappe.has_permission(doctype, doc=docname, ptype="read"):
		frappe.throw(
			frappe._("You do not have permission to read this record."),
			frappe.PermissionError,
		)

	requirements = frappe.get_all(
		"AI Document Requirement",
		filters={"target_doctype": doctype, "is_active": 1},
		fields=["document_type_key", "label"],
		order_by="label asc",
	)
	if not requirements:
		return {"present": [], "missing": []}

	processed_keys = set(
		frappe.db.get_all(
			"AI Processing Log",
			filters={
				"linked_doctype": doctype,
				"linked_docname": docname,
				"processing_status": "Completed",
			},
			pluck="document_type_key",
		)
	)

	present, missing = [], []
	for req in requirements:
		entry = {"document_type_key": req.document_type_key, "label": req.label or req.document_type_key}
		(present if req.document_type_key in processed_keys else missing).append(entry)

	return {"present": present, "missing": missing}


@frappe.whitelist()
def confirm_extraction(
	log_name: str,
	doctype: str | None = None,
	docname: str | None = None,
) -> dict:
	"""
	Accept a low-confidence extraction result and fire its post-processors.

	Called after the user reviews and accepts a result held below the
	confidence threshold configured in AI Settings.  Post-processors get the
	values the user corrected (submit_correction), not the first reading.
	Only the log owner or a System Manager may confirm.
	"""
	_assert_log_access(log_name)
	ensure_record_access(doctype, docname)

	fire_post_processors(
		frappe.db.get_value("AI Processing Log", log_name, "document_type_key"),
		{"extracted_data": review.confirmed_values(log_name), "log_name": log_name},
		doctype,
		docname,
	)
	return {"ok": True}
