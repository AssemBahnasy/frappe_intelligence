# Copyright (c) 2026, AssemBahnasy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import now_datetime

from frappe_intelligence.documents import review
from frappe_intelligence.providers import Message, Reply, ToolCall

TITLE_LENGTH = 80
# Messages sent to the model per turn; older ones stay stored and visible.
HISTORY_LIMIT = 40
STOPPED_NOTICE = "stopped"
# Tool results the model reads for proposals the user did not approve.
REJECTED_RESULT = "The user rejected this change. Do not try it again unless they ask."
MOVED_ON_RESULT = "The user did not confirm this change and sent a new message instead."


class AIConversation(Document):
	def validate(self):
		first = next((row for row in self.messages if row.role == "user"), None)
		if not self.title and first:
			# A question sent as just a file is named after the file.
			files = ", ".join(file["file_name"] for file in frappe.parse_json(first.attachments or "[]"))
			self.title = (first.content or files)[:TITLE_LENGTH]

	def add_user_message(
		self, text: str, context: dict | None = None, attachments: list | None = None
	) -> None:
		self.append(
			"messages",
			{"role": "user", "content": text, "context": _json(context), "attachments": _json(attachments)},
		)
		self.last_user_message_at = now_datetime()

	def unread_attachments(self) -> list[ToolCall]:
		"""read_document calls for the files sent with the latest question, until they have been made."""
		row = self.messages[-1] if self.messages else None
		if not row or row.role != "user" or not row.attachments:
			return []
		return [
			ToolCall(id=f"read_{frappe.generate_hash(length=10)}", name="read_document", arguments=file)
			for file in frappe.parse_json(row.attachments)
		]

	def add_reply(self, reply: Reply) -> None:
		self.append(
			"messages",
			{
				"role": "assistant",
				"content": reply.text,
				"tool_calls": _json([vars(call) for call in reply.tool_calls]),
				"raw": _json(reply.raw),
				"raw_provider": reply.raw_provider,
			},
		)

	def add_tool_result(self, call: ToolCall, content: str, is_error: bool = False) -> None:
		self.append(
			"messages",
			{
				"role": "tool",
				"tool_name": call.name,
				"tool_call_id": call.id,
				"content": content,
				"is_error": int(is_error),
			},
		)

	def add_proposal(self, call: ToolCall, preview: dict, content: str | None = None) -> None:
		"""Waits for the user: a change (its result comes once they decide) or a document reading to
		review (`content` holds the reading until they confirm it)."""
		self.append(
			"messages",
			{
				"role": "tool",
				"tool_name": call.name,
				"tool_call_id": call.id,
				"approval": "Pending",
				"preview": _json(preview),
				"content": content,
			},
		)

	def decide(self, call_id: str, approve: bool):
		row = next((row for row in self.messages if row.tool_call_id == call_id and row.role == "tool"), None)
		if not row or row.approval != "Pending":
			frappe.throw(frappe._("This change is no longer waiting for a decision."))
		row.approval = "Approved" if approve else "Rejected"
		if not approve:
			row.content = review.DISCARDED_RESULT if _is_review(row) else REJECTED_RESULT
		return row

	def pending_proposals(self) -> list:
		return [row for row in self.messages if row.approval == "Pending"]

	def reject_pending(self) -> None:
		for row in self.pending_proposals():
			row.approval = "Rejected"
			row.content = review.unconfirmed(row.content) if _is_review(row) else MOVED_ON_RESULT

	def approved_to_run(self) -> list[tuple]:
		"""Approved changes not run yet, with the tool call each answers."""
		calls = {
			call["id"]: ToolCall(**call)
			for row in self.messages
			if row.role == "assistant" and row.tool_calls
			for call in frappe.parse_json(row.tool_calls)
		}
		return [
			(row, calls[row.tool_call_id])
			for row in self.messages
			if row.approval == "Approved" and not row.content and row.tool_call_id in calls
		]

	def add_stopped(self) -> None:
		"""Marks the turn as stopped by the user; system rows are never sent to the model."""
		self.append("messages", {"role": "system", "content": STOPPED_NOTICE})

	def add_error(self, text: str) -> None:
		"""Shown to the user, never sent back to the model."""
		self.append("messages", {"role": "assistant", "content": text, "is_error": 1})

	def add_fixed_reply(self, text: str, off_topic: bool = False) -> None:
		"""A reply written without AI (a workflow's questions and redirects); the model reads it as its own."""
		self.append("messages", {"role": "assistant", "content": text, "off_topic": int(off_topic)})

	def current_question(self) -> tuple[str, dict | None]:
		"""Text and page context of the latest user message."""
		row = next(row for row in reversed(self.messages) if row.role == "user")
		return row.content, frappe.parse_json(row.context) if row.context else None

	def provider_messages(self) -> list[Message]:
		rows = [
			row
			for row in self.messages
			if row.role != "system"
			and not (row.is_error and row.role != "tool")
			and row.approval != "Pending"
		]
		current_turn = max((i for i, row in enumerate(rows) if row.role == "user"), default=0)
		start = min(current_turn, max(len(rows) - HISTORY_LIMIT, 0))
		return [_to_message(row) for row in _from_user_turn(rows[start:])]

	@staticmethod
	def clear_old_logs(days=90):
		table = frappe.qb.DocType("AI Conversation")
		names = (
			frappe.qb.from_(table).select(table.name).where(table.modified < (Now() - Interval(days=days)))
		).run(pluck=True)
		if names:
			frappe.db.delete(
				"AI Conversation Message", {"parenttype": "AI Conversation", "parent": ("in", names)}
			)
			frappe.db.delete("AI Conversation", {"name": ("in", names)})


def _json(value) -> str | None:
	"""JSON fields reject lists, so store everything as text."""
	return frappe.as_json(value, indent=None) if value else None


def _is_review(row) -> bool:
	return review.is_review(frappe.parse_json(row.preview) if row.preview else None)


def _from_user_turn(rows: list) -> list:
	"""A trimmed history must start at a user message, never between a tool call and its result."""
	start = next((i for i, row in enumerate(rows) if row.role == "user"), len(rows))
	return rows[start:]


def _to_message(row) -> Message:
	return Message(
		role=row.role,
		content=row.content or "",
		tool_calls=[ToolCall(**call) for call in frappe.parse_json(row.tool_calls or "[]")],
		tool_call_id=row.tool_call_id,
		name=row.tool_name,
		raw=frappe.parse_json(row.raw) if row.raw else None,
		raw_provider=row.raw_provider,
	)
