"""Read the user's answer into the fields the current step still needs, with the AI provider
(documents/extractor.py).

The model reads the question it was answering too, so a bare "Riyadh" or a number lands in the right
field. Files sent with the answer are read with it. The caller passes only the fields still empty: a
small model tends to copy a new answer into fields already answered.
"""

from __future__ import annotations

from types import SimpleNamespace

from frappe_intelligence.documents import extractor

HINT = "The {label} the user gave in their answer or attached document: the value alone, without its label; null if not given."


def read(text: str, fields: dict[str, str], asked: str = "", documents: str = "") -> dict[str, str]:
	"""`{field key: value}` for each of `fields` (`{field key: label}`) the answer gives.

	Raises ProviderError when the AI cannot be reached, so an outage is not taken for an answer that
	gave nothing."""
	rules = [
		SimpleNamespace(field_key=key, llm_hint=HINT.format(label=label), extraction_strategy="AI")
		for key, label in fields.items()
	]
	if not rules or not (text or documents):
		return {}
	exchange = "\n".join(
		part
		for part in (
			f"Assistant: {asked}" if asked else "",
			f"User: {text}",
			f"Attached documents:\n{documents}" if documents else "",
		)
		if part
	)
	found, _confidence = extractor.extract(exchange, rules, strict=True)
	return {key: value for key, value in found.items() if value}
