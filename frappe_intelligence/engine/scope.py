"""Pre-LLM scope gate for AI Workflow enforcement.

Call check_scope() before any LLM call. When the user's message is out of
scope, the configured out_of_scope_reply is returned immediately — no tokens
consumed, no network call made.
"""

import re
import math
from collections import Counter

import frappe


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_scope(text: str, workflow_doc) -> tuple[bool, str | None]:
    """Return (in_scope, redirect_reply).

    :param text: The user's raw input.
    :param workflow_doc: An AI Workflow frappe Document (already fetched).
    :returns: (True, None) when in scope; (False, out_of_scope_reply) when not.
    """
    if not workflow_doc or not workflow_doc.scope_description:
        return True, None

    # Per-workflow excluded keywords bypass the keyword gate entirely.
    # Useful for domain-specific terms that match generic off-topic patterns.
    excluded = _parse_excluded_keywords(getattr(workflow_doc, "excluded_keywords", None))
    text_lower = text.lower()
    skip_keyword_gate = any(kw in text_lower for kw in excluded)

    if not skip_keyword_gate and _keyword_gate(text):
        reply = workflow_doc.out_of_scope_reply or _default_redirect()
        return False, reply

    scope_text = workflow_doc.scope_description
    similarity = _cosine_similarity(text, scope_text)

    threshold = _get_threshold()
    if similarity < threshold:
        reply = workflow_doc.out_of_scope_reply or _default_redirect()
        return False, reply

    return True, None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Patterns that are almost always off-topic in a business workflow context.
_OFF_TOPIC_PATTERNS = [
    r"\b(your age|how old are you|who made you|who created you|are you (human|a robot|an ai|real))\b",
    r"\b(write me a (poem|story|song|joke|essay))\b",
    r"\b(tell me a joke|make me laugh)\b",
    r"\b(what('s| is) the (weather|time|date) (today|now|in|at))\b",
    r"\b(translate (this|the following) (to|into))\b",
    r"\b(what is [0-9]+ (plus|minus|times|divided by|multiplied by) [0-9]+)\b",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _OFF_TOPIC_PATTERNS]


def _keyword_gate(text: str) -> bool:
    """Fast regex pre-filter — catches obviously off-topic patterns."""
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _tokenise(text: str) -> list[str]:
    """Lowercase word tokens, stripping punctuation."""
    return re.findall(r"[a-zA-Z؀-ۿ]+", text.lower())


def _tf_idf_vector(tokens: list[str], corpus_tokens: list[str]) -> dict[str, float]:
    """Simple TF-IDF vector over two documents (user text vs scope_description)."""
    tf = Counter(tokens)
    total = len(tokens) or 1
    vocab = set(tokens) | set(corpus_tokens)
    corpus_tf = Counter(corpus_tokens)
    corpus_total = len(corpus_tokens) or 1

    vector = {}
    for term in vocab:
        tf_val = tf.get(term, 0) / total
        # IDF: log((1 + N) / (1 + df)) + 1, N=2 (two docs)
        df = (1 if tf.get(term, 0) > 0 else 0) + (1 if corpus_tf.get(term, 0) > 0 else 0)
        idf = math.log((1 + 2) / (1 + df)) + 1
        vector[term] = tf_val * idf

    return vector


def _cosine_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two raw texts using TF-IDF weighting."""
    tokens_a = _tokenise(text_a)
    tokens_b = _tokenise(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    vec_a = _tf_idf_vector(tokens_a, tokens_b)
    vec_b = _tf_idf_vector(tokens_b, tokens_a)

    dot = sum(vec_a.get(t, 0) * vec_b.get(t, 0) for t in vec_a)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def _get_threshold() -> float:
    """Scope similarity threshold — reads from AI Settings, defaults to 0.05.

    Kept low intentionally: the keyword gate handles obvious off-topic content;
    the cosine check is a backstop for very short inputs with zero overlap.
    Operators can tighten it in AI Settings if needed.
    """
    try:
        threshold = frappe.db.get_single_value("AI Settings", "scope_similarity_threshold")
        return float(threshold) if threshold is not None else 0.05
    except Exception:
        return 0.05


def _parse_excluded_keywords(raw: str | None) -> list[str]:
    """Parse excluded_keywords field (one keyword/phrase per line) to lowercase list."""
    if not raw:
        return []
    return [line.strip().lower() for line in raw.splitlines() if line.strip()]


def _default_redirect() -> str:
    return (
        "I can only help with tasks within the scope of this service. "
        "Please ask me something related to what I can assist you with."
    )
