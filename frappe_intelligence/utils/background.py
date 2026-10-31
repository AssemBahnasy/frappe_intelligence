"""Short jobs one browser waits for: the text Write with AI writes, a voice recording's text. The
result arrives on the `fi_job` realtime event; a browser that missed it asks with the job id
(`api.jobs.job_result`). The panel's answers use agent/runs.py instead: they stream and can stop."""

from __future__ import annotations

import frappe
from frappe import _

from frappe_intelligence.providers import ProviderError
from frappe_intelligence.utils.optional import MissingPackage

EVENT = "fi_job"
QUEUE = "long"
TIMEOUT = 600  # seconds; local models can be slow
RESULT_KEY = "fi_job:{0}:{1}"
RESULT_TTL = 600
# Their message is for the user; anything else is logged and reported in general terms.
USER_ERRORS = (ProviderError, MissingPackage, frappe.ValidationError)


def start(target: str, **arguments) -> str:
	"""Run `target(**arguments)` in the background; returns the job id its result comes back with.

	Not `method` / `kwargs`: frappe.enqueue takes those names itself."""
	job = frappe.generate_hash(length=16)
	frappe.enqueue(
		"frappe_intelligence.utils.background.run",
		queue=QUEUE,
		timeout=TIMEOUT,
		job_id=job,
		job=job,
		target=target,
		arguments=arguments,
	)
	return job


def run(job: str, target: str, arguments: dict) -> None:
	"""Background job: run it, keep the result for the user a while and tell their browser."""
	try:
		result = {"value": frappe.get_attr(target)(**arguments)}
	except USER_ERRORS as exc:
		result = {"error": str(exc)}
	except Exception:
		frappe.log_error(f"Assistant job {job} ({target}) failed")
		result = {"error": _("This could not be done. Please try again.")}
	frappe.cache.set_value(result_key(job), result, expires_in_sec=RESULT_TTL)
	frappe.publish_realtime(EVENT, {"job": job, **result}, user=frappe.session.user)


def result(job: str) -> dict:
	"""`{value}`, `{error}` or `{pending: true}`; only the user who started the job finds it."""
	return frappe.cache.get_value(result_key(job)) or {"pending": True}


def result_key(job: str) -> str:
	return RESULT_KEY.format(frappe.session.user, job)
