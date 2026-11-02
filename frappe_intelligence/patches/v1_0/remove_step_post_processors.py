"""Workflow steps no longer take post-processors: nothing ever read them. Post-processors run by
document type (documents/pipeline.fire_post_processors)."""

import frappe


def execute():
	frappe.delete_doc("DocType", "AI Workflow Post Processor", ignore_missing=True, force=True)
	# Deleting a DocType keeps its table.
	frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabAI Workflow Post Processor`")
