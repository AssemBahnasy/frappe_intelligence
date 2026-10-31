"""Read a file: the agent loop calls this for every file sent with a question (loop._read_attachments)."""

from __future__ import annotations

import frappe
from frappe import _, _lt

from frappe_intelligence.agent.tools import AgentTool, ToolError
from frappe_intelligence.documents import review
from frappe_intelligence.utils.file_utils import validate_file_access


def read_document(arguments: dict) -> dict:
	file_url = arguments["file_url"]
	validate_file_access(file_url)
	try:
		return review.read(file_url)
	except (OSError, ValueError, ImportError) as exc:
		# Missing file, unreadable content or no OCR library: the details are for the Error Log.
		frappe.log_error(f"Assistant could not read {file_url}")
		raise ToolError(_("The file could not be read. It may be damaged or empty.")) from exc


TOOLS = [
	AgentTool(
		name="read_document",
		description=(
			"Read a PDF, image or text file by its file URL. Returns its text; when it matches a "
			"document template, the user first checks the values read from it."
		),
		parameters={
			"type": "object",
			"properties": {"file_url": {"type": "string"}, "file_name": {"type": "string"}},
			"required": ["file_url"],
		},
		run=read_document,
		label=_lt("Reading {file_name}"),
		review=True,
	),
]
