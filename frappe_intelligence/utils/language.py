"""Which language the assistant replies in (AI Settings → Response Language)."""

from contextlib import contextmanager

import frappe

ARABIC_SHARE = 0.2


def allowed_languages() -> list[tuple[str, str]]:
	"""`[(code, name)]` from AI Settings; empty means mirror the user's language."""
	rows = frappe.get_cached_doc("AI Settings").response_language
	return [
		(row.language, frappe.get_cached_value("Language", row.language, "language_name") or row.language)
		for row in rows
	]


def detect_language(text: str) -> str:
	stripped = text.strip()
	if not stripped:
		return "en"
	arabic = sum(1 for char in stripped if "؀" <= char <= "ۿ")
	return "ar" if arabic / len(stripped) > ARABIC_SHARE else "en"


def reply_language(text: str) -> str:
	"""The language code of the reply to `text`: AI Settings' choice, else Arabic for an Arabic
	message, else the desk language."""
	allowed = dict(allowed_languages())
	detected = detect_language(text)
	if allowed:
		return detected if detected in allowed else next(iter(allowed))
	return "ar" if detected == "ar" else frappe.local.lang


def language_rule(text: str) -> str:
	"""The instruction that pins the reply language for this message."""
	allowed = dict(allowed_languages())
	if allowed:
		return _only(allowed[reply_language(text)])
	if detect_language(text) == "ar":
		return _only("Arabic")
	return "Reply in the same language as the user's message, without adding translations."


@contextmanager
def replying_to(text: str):
	"""`_()` translates into the reply language: for replies written without AI."""
	# A background job applies its user's language at the first `_()`; let that happen before ours.
	frappe._("")
	desk = frappe.local.lang
	frappe.local.lang = reply_language(text)
	try:
		yield
	finally:
		frappe.local.lang = desk


def _only(name: str) -> str:
	return (
		f"Reply only in {name}. Do not add translations or text in any other language.\n"
		f"أجب باللغة {name} فقط، دون ترجمة أو نص بلغة أخرى."
	)
