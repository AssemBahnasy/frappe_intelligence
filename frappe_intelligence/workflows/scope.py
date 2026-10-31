"""The topic gate: messages outside a workflow get its redirect without a model call.

Two checks, both without AI:
	is_off_topic  phrases that are never part of a business workflow (jokes, weather, …)
	is_related    for a message that answered nothing: does it share words with the workflow's
	              mandate and the current step? A short answer ("Riyadh") shares none, so this
	              runs only after reading the answer found no values in it, and only when the
	              message and the mandate are in the same language.
A line of the workflow's Excluded Keywords in the message lets it through both.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import frappe
from frappe import _

from frappe_intelligence.utils.language import detect_language
from frappe_intelligence.workflows import steps

DEFAULT_THRESHOLD = 0.05
# Words every question shares ("what is the …"); left out, so only the subject is compared.
_STOPWORDS = set(
	"the and are was were for from with this that these those have has had not but can could would should "
	"will you your what which who whom why how when where about they them their there here its our out all "
	"any before after into tell give please just also some more than then".split()
) | {"ماذا", "هذا", "هذه", "التي", "الذي", "إلى", "على", "كيف", "لماذا", "متى", "أين"}
_OFF_TOPIC = [
	re.compile(pattern, re.IGNORECASE)
	for pattern in (
		r"\b(your age|how old are you|who made you|who created you|are you (human|a robot|an ai|real))\b",
		r"\b(write me a (poem|story|song|joke|essay))\b",
		r"\b(tell me a joke|make me laugh)\b",
		r"\b(what('s| is) the (weather|time|date) (today|now|in|at))\b",
		r"\b(translate (this|the following) (to|into))\b",
		r"\b(what is [0-9]+ (plus|minus|times|divided by|multiplied by) [0-9]+)\b",
	)
]


def is_off_topic(text: str, workflow) -> bool:
	if not workflow.scope_description or _excluded(text, workflow):
		return False
	return any(pattern.search(text) for pattern in _OFF_TOPIC)


def is_related(text: str, workflow, step) -> bool:
	if not workflow.scope_description or _excluded(text, workflow):
		return True
	topic = " ".join([workflow.scope_description, step.prompt_to_user or "", *steps.fields(step).values()])
	if detect_language(text) != detect_language(topic):
		return True  # no shared words to compare; the model keeps to the mandate
	return _cosine_similarity(text, topic) >= _threshold()


def redirect(workflow) -> str:
	return workflow.out_of_scope_reply or _("That's outside this workflow.")


def _excluded(text: str, workflow) -> bool:
	lowered = text.lower()
	keywords = (line.strip().lower() for line in (workflow.excluded_keywords or "").splitlines())
	return any(keyword and keyword in lowered for keyword in keywords)


def _threshold() -> float:
	"""AI Settings → Scope Similarity Threshold. Kept low: the phrase check catches the obvious cases."""
	value = frappe.db.get_single_value("AI Settings", "scope_similarity_threshold")
	return float(value) if value else DEFAULT_THRESHOLD


def _tokens(text: str) -> list[str]:
	words = re.findall(r"[a-zA-Z؀-ۿ0-9]+", text.lower())
	return [word for word in words if len(word) >= 3 and word not in _STOPWORDS]


def _tf_idf(tokens: list[str], other: list[str]) -> dict[str, float]:
	"""TF-IDF over the two texts: words both share weigh less than words only one has."""
	counts, other_counts = Counter(tokens), Counter(other)
	total = len(tokens) or 1
	vector = {}
	for term in set(tokens) | set(other):
		documents = (term in counts) + (term in other_counts)
		vector[term] = counts.get(term, 0) / total * (math.log(3 / (1 + documents)) + 1)
	return vector


def _cosine_similarity(text_a: str, text_b: str) -> float:
	tokens_a, tokens_b = _tokens(text_a), _tokens(text_b)
	if not tokens_a or not tokens_b:
		return 0.0
	vector_a, vector_b = _tf_idf(tokens_a, tokens_b), _tf_idf(tokens_b, tokens_a)
	dot = sum(value * vector_b.get(term, 0) for term, value in vector_a.items())
	norm = math.sqrt(sum(v * v for v in vector_a.values())) * math.sqrt(sum(v * v for v in vector_b.values()))
	return dot / norm if norm else 0.0
