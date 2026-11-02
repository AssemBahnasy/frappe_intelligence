import frappe
from frappe.model.document import Document


class AIDocumentTemplate(Document):
	def validate(self):
		if self.document_type_key:
			self.document_type_key = self.document_type_key.strip().lower().replace(" ", "_")

	def get_keywords(self) -> list[str]:
		"""Return a list of stripped detection keywords."""
		if not self.detection_keywords:
			return []
		return [kw.strip().lower() for kw in self.detection_keywords.split(",") if kw.strip()]
