"""Records the tutorial's demo videos (`bench fi-record-tutorial`). See docs/tutorial/videos.md.

A temporary desk user, in each language in turn, plays the scenes of public/js/tutorial/demos.js
through recorder.cjs. The user and everything it left behind are removed afterwards.
"""

import json
import os
import subprocess

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.permissions import AUTOMATIC_ROLES
from frappe.sessions import clear_sessions

RECORDER = "tutorial.recorder@example.com"
APP = frappe.get_app_path("frappe_intelligence")
SCRIPT = os.path.join(APP, "tutorial", "recorder.cjs")
VIDEOS = os.path.join(APP, "public", "tutorial")
TIMINGS = os.path.join(APP, "public", "js", "tutorial", "videos.json")


def record(topics: list[str], languages: list[str], first_name: str) -> None:
	if not frappe.conf.developer_mode:
		frappe.throw("Demo videos are recorded on a development site (developer_mode).")
	make_user(first_name)
	try:
		base_url, sid = frappe.utils.get_url(), session()
		for lang in languages:
			frappe.db.set_value("User", RECORDER, "language", lang)
			frappe.db.commit()
			frappe.clear_cache(user=RECORDER)
			save_timings(lang, run_recorder(base_url, sid, lang, topics))
	finally:
		remove_user()


def run_recorder(base_url: str, sid: str, lang: str, topics: list[str]) -> dict:
	args = {
		"base_url": base_url,
		"sid": sid,
		"lang": lang,
		"topics": topics,
		"videos_dir": VIDEOS,
	}
	# The session goes in the environment, not the command line other users can list.
	env = {**os.environ, "FI_DEMO": json.dumps(args)}
	result = subprocess.run(["node", SCRIPT], cwd=APP, env=env, stdout=subprocess.PIPE, text=True, check=True)
	return json.loads(result.stdout.strip().splitlines()[-1])


def save_timings(lang: str, recorded: dict) -> None:
	"""videos.json: {topic: {lang: {duration, steps}}}, the seconds where each step starts."""
	timings = {}
	if os.path.exists(TIMINGS):
		with open(TIMINGS) as f:
			timings = json.load(f)
	for topic, timing in recorded.items():
		timings.setdefault(topic, {})[lang] = timing
	with open(TIMINGS, "w") as f:
		json.dump(dict(sorted(timings.items())), f, indent=1, sort_keys=True)
		f.write("\n")


def make_user(first_name: str) -> None:
	remove_user()
	# Every desk role, so a scene can open any page of the site.
	roles = frappe.get_all(
		"Role", filters={"desk_access": 1, "disabled": 0, "name": ["not in", AUTOMATIC_ROLES]}, pluck="name"
	)
	frappe.get_doc(
		{
			"doctype": "User",
			"email": RECORDER,
			"first_name": first_name,
			"send_welcome_email": 0,
			"roles": [{"role": role} for role in roles],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache(user=RECORDER)


def session() -> str:
	frappe.utils.set_request(path="/")
	frappe.local.cookie_manager = CookieManager()
	frappe.local.login_manager = LoginManager()
	frappe.local.login_manager.login_as(RECORDER)
	frappe.db.commit()
	return frappe.session.sid


def remove_user() -> None:
	if not frappe.db.exists("User", RECORDER):
		return
	clear_sessions(RECORDER, force=True)
	frappe.delete_doc("User", RECORDER, force=True, ignore_permissions=True, delete_permanently=True)
	for doctype in ("Route History", "Activity Log", "Access Log"):
		frappe.db.delete(doctype, {"user": RECORDER})
	frappe.db.delete("__UserSettings", {"user": RECORDER})
	frappe.db.delete("DefaultValue", {"parent": RECORDER})
	frappe.db.delete("Deleted Document", {"deleted_name": RECORDER})
	frappe.db.commit()
