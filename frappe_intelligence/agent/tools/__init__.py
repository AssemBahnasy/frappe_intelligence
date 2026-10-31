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
AGENT_ONLY = frozenset({AGENT})
SAVEPOINT = "fi_assistant_tool"


class ToolError(Exception):
	"""A failure the model should read and recover from."""


@dataclass(frozen=True)
class AgentTool:
	name: str
	description: str
	parameters: dict
	run: Callable[[dict], Any]
	label: Any  # a lazy translation (frappe._lt) with argument names, e.g. {doctype} or {file_name}
	modes: frozenset[str] = READ_MODES
	# The result carries an `action` the browser performs (open a form, draw a chart).
	browser_action: bool = False
	# Changes data: `preview` builds the approval card; `run` happens only after the user confirms.
	preview: Callable[[dict], dict] | None = None
	# The result may carry a `review` card: the turn then waits for the user to check it.
	review: bool = False

	@property
	def needs_approval(self) -> bool:
		return self.preview is not None

	def spec(self) -> dict:
		return {"name": self.name, "description": self.description, "parameters": self.parameters}

	def step_label(self, arguments: dict) -> str:
		return str(self.label).format_map(_Blank(arguments))


class _Blank(dict):
	"""Arguments for a step label; one the model left out shows as empty."""

	def __missing__(self, key: str) -> str:
		return ""


@dataclass
class Outcome:
	content: str = ""
	is_error: bool = False
	action: dict | None = None
	preview: dict | None = None
	review: dict | None = None


def registry() -> dict[str, AgentTool]:
	from frappe_intelligence.agent.tools import changes, desk, documents, frappe_data, knowledge, reports

	modules = (frappe_data, reports, knowledge, documents, desk, changes)
	return {tool.name: tool for module in modules for tool in module.TOOLS}


def tools_for(mode: str) -> list[AgentTool]:
	return [tool for tool in registry().values() if mode in tool.modes]


def step_label(name: str, arguments: dict) -> str:
	"""What the user sees while the tool runs, e.g. "Reading Customer list"."""
	tool = registry().get(name)
	return tool.step_label(arguments) if tool else name


def needs_approval(name: str) -> bool:
	tool = registry().get(name)
	return bool(tool and tool.needs_approval)


def execute(name: str, arguments: dict, mode: str) -> Outcome:
	"""Run the tool. A failed run is rolled back so a half-made change never stays."""
	tool, outcome = _available(name, mode)
	if not tool:
		return outcome
	frappe.db.savepoint(SAVEPOINT)
	result = _guarded(name, lambda: tool.run(arguments), outcome)
	if outcome.is_error:
		frappe.db.rollback(save_point=SAVEPOINT)
	else:
		if tool.review:
			outcome.review = result.pop("review", None)
		outcome.content = result if isinstance(result, str) else json.dumps(result, default=json_handler)
		if tool.browser_action:
			outcome.action = result["action"]
	return outcome


def propose(name: str, arguments: dict, mode: str) -> Outcome:
	"""Check a change and build its approval card, without making it."""
	tool, outcome = _available(name, mode)
	if tool:
		outcome.preview = _guarded(name, lambda: tool.preview(arguments), outcome)
	return outcome


def _available(name: str, mode: str) -> tuple[AgentTool | None, Outcome]:
	tool = registry().get(name)
	if not tool or mode not in tool.modes:
		return None, Outcome(_("Tool {0} is not available in {1} mode.").format(name, mode), is_error=True)
	return tool, Outcome()


def _guarded(name: str, call: Callable[[], Any], outcome: Outcome) -> Any:
	"""Run `call`; on failure put the message the model should read into `outcome`."""
	try:
		return call()
	except ToolError as exc:
		outcome.content = str(exc)
	except (frappe.PermissionError, frappe.DoesNotExistError, frappe.ValidationError) as exc:
		outcome.content = _frappe_message(exc)
	except Exception:
		frappe.log_error(f"Assistant tool {name} failed")
		outcome.content = _("The tool failed unexpectedly.")
	outcome.is_error = True


def _frappe_message(exc: Exception) -> str:
	"""frappe.throw also queues a dialog for the browser; the model gets the text instead."""
	frappe.clear_messages()
	return strip_html(str(exc)).strip() or type(exc).__name__
