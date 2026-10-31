"""Search the AI Knowledge Packs administrators write for the assistant."""

from __future__ import annotations

import frappe
from frappe import _lt

from frappe_intelligence.agent.tools import AgentTool

MIN_WORD_LENGTH = 4
RESULT_LIMIT = 3


def search_knowledge(query: str, limit: int = RESULT_LIMIT) -> list[dict]:
	"""Entries of active packs ranked by how many query words they contain."""
	words = [word for word in query.lower().split() if len(word) >= MIN_WORD_LENGTH]
	if not words:
		return []
	packs = frappe.get_all("AI Knowledge Pack", filters={"is_active": 1}, pluck="name")
	if not packs:
		return []
	entries = frappe.get_all(
		"AI Knowledge Entry",
		filters={"parenttype": "AI Knowledge Pack", "parent": ("in", packs)},
		fields=["topic", "content"],
	)
	scored = [(sum(word in f"{e.topic} {e.content}".lower() for word in words), e) for e in entries]
	ranked = sorted((pair for pair in scored if pair[0]), key=lambda pair: pair[0], reverse=True)
	return [{"topic": entry.topic, "content": entry.content} for _, entry in ranked[:limit]]


def knowledge_block(query: str) -> str:
	"""Matching entries as a prompt section, for flows that do not call tools."""
	entries = search_knowledge(query)
	if not entries:
		return ""
	sections = "\n\n".join(f"**{entry['topic']}**\n{entry['content']}" for entry in entries)
	return f"Relevant knowledge:\n\n{sections}\n\n---"


TOOLS = [
	AgentTool(
		name="search_knowledge",
		description=(
			"Search the company's own instructions and policies (AI Knowledge Packs). "
			"Use it for how-to and policy questions before answering from general knowledge."
		),
		parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
		run=lambda arguments: search_knowledge(arguments["query"]),
		label=_lt("Searching the knowledge base"),
	)
]
