"""Which tutorial topics a user has done: a JSON list in their user defaults, which the desk loads
at boot (public/js/tutorial/store.js reads it). The topics themselves live in public/js/tutorial/content.js."""

import json
import re

import frappe
from frappe import _

DONE_KEY = "fi_tutorial_done"
TOPIC_KEY = re.compile(r"^[a-z0-9-]{1,40}$")
MAX_TOPICS = 100


def done_topics(user: str | None = None) -> list[str]:
	try:
		value = json.loads(frappe.defaults.get_user_default(DONE_KEY, user) or "[]")
	except TypeError, ValueError:
		return []
	return [key for key in value if isinstance(key, str)] if isinstance(value, list) else []


def set_done(topic: str, done: bool, user: str | None = None) -> list[str]:
	"""Marks `topic` done or not yet, and returns the topics now done."""
	if not TOPIC_KEY.match(topic or ""):
		frappe.throw(_("This is not a tutorial topic."))
	topics = [key for key in done_topics(user) if key != topic]
	if done:
		topics.append(topic)
	topics = topics[-MAX_TOPICS:]
	# Saving a default clears the user's cached boot, so the next page load sees it.
	frappe.defaults.set_user_default(DONE_KEY, json.dumps(topics), user)
	return topics
