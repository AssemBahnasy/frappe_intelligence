"""Write with AI is on by default; a site that already had AI Settings gets that default too."""

import frappe


def execute():
	frappe.db.set_single_value("AI Settings", "allow_field_writer", 1)
