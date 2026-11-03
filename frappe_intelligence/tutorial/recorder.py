"""Records the tutorial's demo videos (`bench fi-record-tutorial`). See docs/tutorial/videos.md.

A temporary desk user, in each language in turn, plays the scenes of public/js/tutorial/demos.js
through recorder.cjs. The user and everything it left behind are removed afterwards.
"""

import hashlib
import json
import os
import subprocess
import time

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
	recorded = {}
	try:
		base_url, sid = frappe.utils.get_url(), session()
		for lang in languages:
			frappe.db.set_value("User", RECORDER, "language", lang)
			frappe.db.commit()
			frappe.clear_cache(user=RECORDER)
			recorded[lang], failed = run_recorder(base_url, sid, lang, topics)
			if failed:
				frappe.throw(f"Recording in {lang} failed; the error is above.")
	finally:
		# Written once, after every language: with `bench watch` running, writing videos.json
		# rebuilds the tutorial bundle and reloads every open desk, the recorder's own included.
		save_timings(recorded)
		remove_user()


def run_recorder(base_url: str, sid: str, lang: str, topics: list[str]) -> tuple[dict, bool]:
	"""Records `topics` in `lang`; returns the timings of those finished, and whether it failed."""
	args = {
		"base_url": base_url,
		"sid": sid,
		"lang": lang,
		"topics": topics,
		"videos_dir": VIDEOS,
	}
	# The session goes in the environment, not the command line other users can list.
	env = {**os.environ, "FI_DEMO": json.dumps(args)}
	result = subprocess.run(["node", SCRIPT], cwd=APP, env=env, stdout=subprocess.PIPE, text=True)
	timings = {}
	for line in result.stdout.splitlines():
		timings.update(json.loads(line))
	return timings, result.returncode != 0


def save_timings(recorded: dict) -> None:
	"""Adds `{lang: {topic: timing}}` to videos.json, `{topic: {lang: {duration, steps, version}}}`:
	the seconds where each step starts, and a hash of the file, so a new recording is not served
	from the browser's cache."""
	if not any(recorded.values()):
		return
	timings = {}
	if os.path.exists(TIMINGS):
		with open(TIMINGS) as f:
			timings = json.load(f)
	for lang, topics in recorded.items():
		for topic, timing in topics.items():
			with open(os.path.join(VIDEOS, lang, f"{topic}.mp4"), "rb") as f:
				version = hashlib.md5(f.read()).hexdigest()[:8]
			timings.setdefault(topic, {})[lang] = {**timing, "version": version}
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
	# The server may still be finishing the closed browser's last request, which updates the user.
	for attempt in range(3):
		try:
			return _remove_user()
		except frappe.QueryDeadlockError:
			frappe.db.rollback()
			if attempt == 2:
				raise
			time.sleep(2)


def _remove_user() -> None:
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
