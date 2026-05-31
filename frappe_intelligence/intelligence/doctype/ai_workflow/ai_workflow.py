import frappe
from frappe.model.document import Document


class AIWorkflow(Document):
    def validate(self):
        self._validate_step_keys()
        self._warn_active_sessions()

    def _validate_step_keys(self):
        seen = set()
        for step in self.steps or []:
            if step.step_key in seen:
                frappe.throw(
                    f"Duplicate step_key '{step.step_key}' in workflow '{self.workflow_key}'."
                )
            seen.add(step.step_key)

    def _warn_active_sessions(self):
        if not self.is_new():
            count = frappe.db.count(
                "AI Agent Session",
                {"workflow": self.workflow_key, "status": "Active"},
            )
            if count:
                frappe.msgprint(
                    f"There are <b>{count}</b> active session(s) on this workflow. "
                    "Changes may affect in-progress conversations.",
                    title="Active Sessions",
                    indicator="orange",
                )
