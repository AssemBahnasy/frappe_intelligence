"""The result of a short background job the user started (utils/background.py)."""

from __future__ import annotations

import frappe

from frappe_intelligence.utils import background
from frappe_intelligence.utils.access import ensure_assistant_access


@frappe.whitelist()
def job_result(job: str) -> dict:
	"""For a browser that missed the `fi_job` event: `{value}`, `{error}` or `{pending: true}`."""
	ensure_assistant_access()
	return background.result(job)
