"""AI Document Templates: which one a document matches, and the field values it yields."""

from __future__ import annotations

import frappe

from frappe_intelligence.documents import extractor
from frappe_intelligence.documents.heuristic import HeuristicExtractor


def match(raw_text: str, document_type_key: str | None = None):
	"""The active template named by `document_type_key`, else the one whose keywords the text contains most."""
	if document_type_key:
		name = frappe.db.get_value(
			"AI Document Template", {"document_type_key": document_type_key, "is_active": 1}
		)
		if name:
			return frappe.get_doc("AI Document Template", name)

	text = raw_text.lower()
	best, best_score = None, 0
	for template in frappe.get_all(
		"AI Document Template", filters={"is_active": 1}, fields=["name", "detection_keywords"]
	):
		keywords = [word.strip().lower() for word in (template.detection_keywords or "").split(",")]
		score = sum(1 for word in keywords if word and word in text)
		if score > best_score:
			best, best_score = template, score
	return frappe.get_doc("AI Document Template", best.name) if best else None


def extract(raw_text: str, template) -> tuple[dict, float]:
	"""`({field_key: value or None}, confidence)` by the template's Model Preference."""
	preference = (template.model_preference or "Heuristic").strip()
	rules = template.extraction_rules
	if preference == "Heuristic":
		return HeuristicExtractor().extract(raw_text, rules)
	if preference == "VLM":
		return extractor.extract(raw_text, rules)

	# Both: patterns first, the AI provider fills what they missed.
	values, confidence = HeuristicExtractor().extract(raw_text, rules)
	missing = [rule for rule in rules if not values.get(rule.field_key)]
	if not missing:
		return values, confidence
	ai_values, ai_confidence = extractor.extract(raw_text, missing)
	return values | ai_values, (confidence + ai_confidence) / 2
