"""Workflow steps no longer list required documents: no workflow ever asked for them. The requirements
the Workflow Builder made (those with a workflow) go; requirements by DocType stay
(api.documents.get_required_documents). Runs before the DocType loses its Workflow field."""

import frappe


def execute():
	if frappe.db.has_column("AI Document Requirement", "workflow"):
		frappe.db.delete("AI Document Requirement", {"workflow": ("is", "set")})
