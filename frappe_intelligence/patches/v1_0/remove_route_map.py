"""The Route Map belonged to the old floating widget, removed with it."""

import frappe


def execute():
	frappe.delete_doc("DocType", "AI Route Map", ignore_missing=True, force=True)
