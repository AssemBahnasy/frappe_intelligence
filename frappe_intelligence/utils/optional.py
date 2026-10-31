"""Packages an administrator may leave out: they are large (EasyOCR brings torch) and only some
sites need them. Install with `bench pip install -e apps/frappe_intelligence[ocr,voice]`."""

from __future__ import annotations

from importlib.util import find_spec

from frappe import _

OCR = "easyocr"  # photos and scanned PDF pages
VOICE = "faster_whisper"  # voice input


class MissingPackage(ImportError):
	"""A feature needs an optional package this server does not have; the message says which."""


def installed(package: str) -> bool:
	return find_spec(package) is not None


def require(package: str) -> None:
	if not installed(package):
		raise MissingPackage(_MESSAGES[package]())


_MESSAGES = {
	OCR: lambda: _(
		"Reading photos and scanned PDF pages needs the OCR package, which is not installed on this server."
	),
	VOICE: lambda: _("Voice input needs the transcription package, which is not installed on this server."),
}
