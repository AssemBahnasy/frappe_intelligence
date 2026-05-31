import frappe
from frappe.model.document import Document


class AITrainingPair(Document):

    def before_save(self):
        if not self.correction_source:
            self.correction_source = frappe.session.user
