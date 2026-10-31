"""Tools the assistant can call. Each is declared once; the loop, providers and panel read this list."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import frappe
from frappe import _
from frappe.utils import strip_html
from frappe.utils.response import json_handler

ASK = "Ask"
AGENT = "Agent"
READ_MODES = frozenset({ASK, AGENT})


class ToolError(Exception):
	"""A failure the model should read and recover from."""


@dataclass(frozen=True)
class AgentTool:
	name: str
	description: str
	parameters: dict
	run: Callable[[dict], Any]
	label: Any  # a lazy translation (frappe._lt) with {doctype}, {name} or {report_name}
	modes: frozenset[str] = READ_MODES
	# The result carries an `action` the browser performs (open a form, draw a chart).
	browser_action: bool = False

	def spec(self) -> dict:
		return {"name": self.name, "description": self.description, "parameters": self.parameters}

	def step_label(self, arguments: dict) -> str:
		return str(self.label).format(
			**{key: arguments.get(key, "") for key in ("doctype", "name", "report_name")}
		)


@dataclass
class Outcome:
	content: str
	is_error: bool = False
	action: dict | None = None


def registry() -> dict[str, AgentTool]:
	from frappe_intelligence.agent.tools import desk, frappe_data, knowledge, reports

	return {tool.name: tool for module in (frappe_data, reports, knowledge, desk) for tool in module.TOOLS}


def tools_for(mode: str) -> list[AgentTool]:
	return [tool for tool in registry().values() if mode in tool.modes]


def step_label(name: str, arguments: dict) -> str:
	"""What the user sees while the tool runs, e.g. "Reading Customer list"."""
	tool = registry().get(name)
	return tool.step_label(arguments) if tool else name


def execute(name: str, arguments: dict, mode: str) -> Outcome:
	tool = registry().get(name)
	if not tool or mode not in tool.modes:
		return Outcome(_("Tool {0} is not available in {1} mode.").format(name, mode), is_error=True)

	outcome = Outcome("")
	try:
		result = tool.run(arguments)
	except ToolError as exc:
		outcome.content, outcome.is_error = str(exc), True
	except (frappe.PermissionError, frappe.DoesNotExistError, frappe.ValidationError) as exc:
		outcome.content, outcome.is_error = _frappe_message(exc), True
	except Exception:
		frappe.log_error(f"Assistant tool {name} failed")
		outcome.content, outcome.is_error = _("The tool failed unexpectedly."), True
	else:
		outcome.content = result if isinstance(result, str) else json.dumps(result, default=json_handler)
		if tool.browser_action:
			outcome.action = result["action"]
	return outcome


def _frappe_message(exc: Exception) -> str:
	"""frappe.throw also queues a dialog for the browser; the model gets the text instead."""
	frappe.clear_messages()
	return strip_html(str(exc)).strip() or type(exc).__name__
