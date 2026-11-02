"""
utils/file_utils.py
-------------------
File-access security helpers and Frappe URL → filesystem path resolution.

These are the only two places in the codebase that should deal with
``/private/files/`` permission checks or raw ``os.path`` construction.
Import them wherever file validation or path resolution is needed rather
than duplicating the logic.
"""

from __future__ import annotations

import os

import frappe

# Only these two prefixes are valid Frappe-managed file URLs.
_PUBLIC_PREFIX = "/files/"
_PRIVATE_PREFIX = "/private/files/"


def validate_file_access(file_url: str) -> None:
	"""
	Raise an appropriate Frappe exception if the current user cannot read
	*file_url*.

	* Public files (``/files/``) — always accessible to logged-in users.
	* Private files (``/private/files/``) — checked against the File DocType
	  permission of the current user.
	* Any other URL (absolute OS paths, external URLs, etc.) is rejected
	  outright to prevent path-traversal attacks.
	"""
	if not file_url:
		frappe.throw(frappe._("file_url is required."), frappe.MandatoryError)

	if not (file_url.startswith(_PUBLIC_PREFIX) or file_url.startswith(_PRIVATE_PREFIX)):
		frappe.throw(
			frappe._("Invalid file URL. Only /files/ and /private/files/ URLs are accepted."),
			frappe.ValidationError,
		)

	if file_url.startswith(_PRIVATE_PREFIX):
		file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not file_name:
			frappe.throw(
				frappe._("File not found: {0}").format(file_url),
				frappe.DoesNotExistError,
			)
		if not frappe.has_permission("File", doc=file_name, ptype="read"):
			frappe.throw(
				frappe._("You do not have permission to access this file."),
				frappe.PermissionError,
			)


def resolve_file_path(file_url: str) -> str:
	"""
	Convert a Frappe file URL to an absolute filesystem path.

	Only ``/files/`` and ``/private/files/`` URLs are accepted.
	The resolved path is verified to be within the site directory to
	prevent path-traversal via crafted basenames (e.g. ``../../etc/passwd``).

	Raises
	------
	frappe.ValidationError
	    If *file_url* is not a recognised Frappe file URL or the resolved
	    path escapes the site directory.
	"""
	sites_path = frappe.utils.get_site_path()

	if file_url.startswith(_PRIVATE_PREFIX):
		resolved = os.path.realpath(os.path.join(sites_path, "private", "files", os.path.basename(file_url)))
		_assert_within_site(resolved, sites_path)
		return resolved

	if file_url.startswith(_PUBLIC_PREFIX):
		resolved = os.path.realpath(os.path.join(sites_path, "public", "files", os.path.basename(file_url)))
		_assert_within_site(resolved, sites_path)
		return resolved

	frappe.throw(
		frappe._("Invalid file URL. Only /files/ and /private/files/ URLs are accepted."),
		frappe.ValidationError,
	)


def _assert_within_site(resolved_path: str, sites_path: str) -> None:
	"""Raise ValidationError when *resolved_path* escapes *sites_path*."""
	site_root = os.path.realpath(sites_path)
	if not resolved_path.startswith(site_root + os.sep) and resolved_path != site_root:
		frappe.throw(
			frappe._("File path is outside the allowed directory."),
			frappe.ValidationError,
		)
