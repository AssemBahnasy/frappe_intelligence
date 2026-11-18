"""Frappe's own MCP data tools, reused so the assistant reads data exactly as REST API v2 allows."""

from __future__ import annotations

from frappe import _lt
from frappe.mcp import tools as mcp
from frappe.mcp.tools import discover, documents

from frappe_intelligence.agent.tools import AgentTool, ToolError


def _doctype(arguments: dict) -> str | None:
	return arguments.get("doctype")


# (Frappe tool, step label, description when Frappe gives none, the DocType whose records it returns)
READ_TOOLS = (
	(discover.SEARCH_DOCTYPES, _lt("Searching DocTypes"), None, None),
	(discover.GET_DOCTYPE_SCHEMA, _lt("Reading {doctype} fields"), None, None),
	(documents.LIST_DOCUMENTS, _lt("Reading {doctype} list"), None, _doctype),
	(documents.GET_DOCUMENT, _lt("Opening {doctype} {name}"), None, _doctype),
	(
		documents.COUNT_DOCUMENTS,
		_lt("Counting {doctype}"),
		"Count documents of a DocType that match the filters, like frappe.get_count.",
		_doctype,
	),
)


def _wrap(tool: mcp.Tool, label: str, description: str | None, reads) -> AgentTool:
	def run(arguments: dict):
		result = mcp.call({"name": tool.name, "arguments": arguments})
		if result["isError"]:
			raise ToolError(result["content"][0]["text"])
		return result["structuredContent"]

	return AgentTool(
		name=tool.name,
		description=description or tool.description,
		parameters=tool.input_schema,
		run=run,
		label=label,
		reads=reads,
	)


TOOLS = [_wrap(*entry) for entry in READ_TOOLS]
