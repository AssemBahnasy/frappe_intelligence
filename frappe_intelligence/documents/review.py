"""Documents read for the assistant. A document that matches a template comes back as a review card;
the values the user confirms, not the first reading, are what the assistant uses (docs/documents/)."""

from __future__ import annotations

import json

import frappe

from frappe_intelligence.documents import templates
from frappe_intelligence.documents.reader import read_file_text

REVIEW = "review"
TEXT_LIMIT = 6000
VALUE_LIMIT = 1000
DEFAULT_THRESHOLD = 0.6
# Read by the model, so kept in English.
NO_TEMPLATE_NOTE = "No document template matched this file. Read the values you need from the text."
CONFIRMED_NOTE = (
	"These are the values the user checked and corrected: use them exactly. "
	"The text is the original document, only for anything else you need."
)
UNCONFIRMED_NOTE = (
	"The user did not confirm these values and sent a new message instead, which may correct them."
)
DISCARDED_RESULT = "The user discarded the values read from this document. Do not use them unless they ask."


def read(file_url: str) -> dict:
	"""The document's text and, when a template matches, the fields to review under `review`."""
	file_name = (
		frappe.db.get_value("File", {"file_url": file_url}, "file_name") or file_url.rsplit("/", 1)[-1]
	)
	text = read_file_text(file_url)
	template = templates.match(text)
	if not template:
		return {"document": file_name, "note": NO_TEMPLATE_NOTE, "text": text[:TEXT_LIMIT]}

	values, confidence = templates.extract(text, template)
	log = _log(file_url, text, template, values, confidence)
	card = {
		"kind": REVIEW,
		"title": template.document_name,
		"document": file_name,
		"log": log.name,
		"needs_review": confidence < confidence_threshold(),
		"fields": [
			{
				"key": rule.field_key,
				"label": rule.label or rule.field_key,
				"value": values.get(rule.field_key) or "",
			}
			for rule in template.extraction_rules
		],
	}
	return {
		"document": file_name,
		"template": template.document_name,
		"text": text[:TEXT_LIMIT],
		"review": card,
	}


def is_review(card: dict | None) -> bool:
	return bool(card) and card.get("kind") == REVIEW


def confirm(content: str, card: dict, values: dict, conversation: str, context: dict | None) -> str:
	"""The result the model reads once the user confirms: their values. Corrections are kept as a
	training pair, and the reading is linked to the conversation and the record the user has open."""
	labels = {field["key"]: field["label"] for field in card["fields"]}
	original = {field["key"]: field["value"] for field in card["fields"]}
	confirmed = {key: _clean(values.get(key, original[key])) for key in original}
	edited = [key for key in original if confirmed[key] != original[key]]

	log = frappe.get_doc("AI Processing Log", card["log"])
	if edited:
		_training_pair(log, confirmed, conversation)
	_link(log, conversation, context)

	# The checked values come before the long document text, so the model reads them first.
	reading = frappe.parse_json(content)
	result = {"document": reading["document"], "template": reading["template"]}
	# Keyed by field key (often the DocType's own field name), with each field's label beside it.
	result["values"] = {key: value for key, value in confirmed.items() if value}
	result["labels"] = {key: labels[key] for key in result["values"]}
	if edited:
		result["edited_by_user"] = [labels[key] for key in edited]
	result |= {"note": CONFIRMED_NOTE, "text": reading["text"]}
	return json.dumps(result, ensure_ascii=False)


def unconfirmed(content: str) -> str:
	"""The user moved on without confirming: the model keeps the reading, marked as unchecked."""
	return json.dumps({"note": UNCONFIRMED_NOTE, **frappe.parse_json(content)}, ensure_ascii=False)


def confirmed_values(log_name: str) -> dict:
	"""The latest values the user confirmed for a reading, else the reading itself."""
	corrected = frappe.get_all(
		"AI Training Pair",
		filters={"processing_log": log_name},
		pluck="corrected_extraction",
		order_by="creation desc",
		limit=1,
	)
	source = (
		corrected[0] if corrected else frappe.db.get_value("AI Processing Log", log_name, "extracted_data")
	)
	return frappe.parse_json(source or "{}")


def confidence_threshold(workflow_key: str | None = None) -> float:
	"""Below this confidence a reading is marked "Review needed": the workflow's own value, else AI Settings."""
	if workflow_key:
		threshold = frappe.db.get_value("AI Workflow", workflow_key, "confidence_threshold")
		if threshold:
			return float(threshold)
	return float(frappe.get_cached_doc("AI Settings").confidence_threshold or DEFAULT_THRESHOLD)


def _log(file_url: str, text: str, template, values: dict, confidence: float):
	return frappe.get_doc(
		{
			"doctype": "AI Processing Log",
			"file_url": file_url,
			"channel": "desk",
			"processing_status": "Completed",
			"document_template": template.name,
			"document_type_key": template.document_type_key,
			"raw_text": text,
			"extracted_data": frappe.as_json(values),
			"confidence_score": confidence,
		}
	).insert(ignore_permissions=True)


def _training_pair(log, confirmed: dict, conversation: str) -> None:
	frappe.get_doc(
		{
			"doctype": "AI Training Pair",
			"document_template": log.document_template,
			"processing_log": log.name,
			"session": conversation,
			"original_extraction": log.extracted_data,
			"corrected_extraction": frappe.as_json(confirmed),
			"correction_source": frappe.session.user,
		}
	).insert(ignore_permissions=True)


def _link(log, conversation: str, context: dict | None) -> None:
	link = {"session": conversation}
	doctype, name = (context or {}).get("doctype"), (context or {}).get("docname")
	# The record's document checklist counts linked readings, so only someone who may edit it links one.
	if doctype and name and frappe.has_permission(doctype, "write", name):
		link |= {"linked_doctype": doctype, "linked_docname": name}
	log.db_set(link, update_modified=False)


def _clean(value) -> str:
	return str(value).strip()[:VALUE_LIMIT] if value is not None else ""
