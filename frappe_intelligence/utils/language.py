"""Which language the assistant replies in (AI Settings → Response Language)."""

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


def language_rule(text: str) -> str:
	"""The instruction that pins the reply language for this message."""
	allowed = allowed_languages()
	if allowed:
		codes = [code for code, _ in allowed]
		detected = detect_language(text)
		code = detected if detected in codes else codes[0]
		return _only(dict(allowed)[code])
	if detect_language(text) == "ar":
		return _only("Arabic")
	return "Reply in the same language as the user's message, without adding translations."


def _only(name: str) -> str:
	return (
		f"Reply only in {name}. Do not add translations or text in any other language.\n"
		f"أجب باللغة {name} فقط، دون ترجمة أو نص بلغة أخرى."
	)
