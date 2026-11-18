"""Downloading a sheet the assistant compiled (agent/sheets.py)."""

from __future__ import annotations

import frappe
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.desk.utils import provide_binary_file

from frappe_intelligence.agent import sheets
from frappe_intelligence.utils.access import ensure_assistant_access


@frappe.whitelist(methods=["POST"])
def download_sheet(conversation: str, call_id: str, file_format: str = "Excel") -> None:
	"""The sheet as a file, built again from the conversation's stored rows once the user's Export
	rights on every DocType it was built from are checked again; logged as an Export."""
	ensure_assistant_access()
	doc = frappe.get_doc("AI Conversation", conversation)
	doc.check_permission("read")
	title, extension, content = sheets.sheet_file(doc, call_id, file_format)
	make_access_log(report_name=title, file_type=file_format, method="Export")
	provide_binary_file(title, extension, content)
