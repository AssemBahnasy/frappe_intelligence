"""
reader.py
---------
Unified document-reading layer.

- Digital PDFs  → pypdf  (embedded text, lossless)
- Scanned images (JPG / PNG / etc.) → EasyOCR  (ar + en, CPU-safe)
- Plain text    → direct UTF-8 read

Public function
---------------
    get_text(file_path: str) -> str
        Accepts an *absolute filesystem path* (already resolved from the
        Frappe file URL by the orchestrator via read_file_text).

    read_file_text(file_url: str) -> str
        Accepts a Frappe file_url, resolves it, then calls get_text().
"""
from __future__ import annotations

import os
import threading

import frappe

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
_PDF_EXT = ".pdf"

# EasyOCR reader is expensive to initialise – cache one instance per process.
_ocr_lock = threading.Lock()
_ocr_reader = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_text(file_path: str) -> str:
    """
    Extract and return all text from *file_path*.

    Parameters
    ----------
    file_path:
        Absolute path to the file on the local filesystem.

    Returns
    -------
    str — extracted text (may be empty if the document has no readable content).

    Raises
    ------
    FileNotFoundError  if *file_path* does not exist.
    ValueError         if the file extension is not supported.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in _IMAGE_EXTS:
        return _ocr_image(file_path)
    if ext == _PDF_EXT:
        return _extract_pdf(file_path)

    # Fallback: plain text
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        raise ValueError(f"Cannot read file {file_path}: {exc}") from exc


def read_file_text(file_url: str) -> str:
    """
    Resolve a Frappe *file_url* to an absolute path and return its text.

    This is the function called by the orchestrator.
    """
    abs_path = _resolve_path(file_url)
    return get_text(abs_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_path(file_url: str) -> str:
    """
    Map a Frappe file_url to an absolute filesystem path.

    Only ``/files/`` and ``/private/files/`` URLs are accepted.  The
    resolved path is verified to be within the site directory to prevent
    path-traversal attacks via crafted basenames or unexpected prefixes.

    Raises
    ------
    frappe.ValidationError
        If *file_url* is not a recognised Frappe file URL or the resolved
        path would escape the site directory.
    """
    site_root = os.path.realpath(frappe.utils.get_site_path())

    if file_url.startswith("/files/"):
        resolved = os.path.realpath(
            frappe.get_site_path("public", "files", os.path.basename(file_url))
        )
    elif file_url.startswith("/private/files/"):
        resolved = os.path.realpath(
            frappe.get_site_path("private", "files", os.path.basename(file_url))
        )
    else:
        frappe.throw(
            frappe._("Invalid file URL. Only /files/ and /private/files/ are accepted."),
            frappe.ValidationError,
        )

    if not resolved.startswith(site_root + os.sep) and resolved != site_root:
        frappe.throw(
            frappe._("File path is outside the allowed directory."),
            frappe.ValidationError,
        )

    return resolved


def _get_ocr_reader():
    """Return a cached EasyOCR Reader (lazy-initialised, thread-safe)."""
    global _ocr_reader
    if _ocr_reader is None:
        with _ocr_lock:
            if _ocr_reader is None:
                try:
                    import easyocr  # noqa: PLC0415
                    _ocr_reader = easyocr.Reader(["ar", "en"], gpu=False)
                except ImportError as exc:
                    raise ImportError(
                        "easyocr is required for image OCR. "
                        "Install it with: pip install easyocr"
                    ) from exc
    return _ocr_reader


def _ocr_image(path: str) -> str:
    """
    Extract text from an image file using EasyOCR (Arabic + English).

    EasyOCR returns a list of (bbox, text, confidence) tuples when
    detail=1 (default) or plain strings when detail=0.  We use detail=0
    for simplicity and join lines with newlines.
    """
    reader = _get_ocr_reader()
    results = reader.readtext(path, detail=0, paragraph=True)
    return "\n".join(str(line) for line in results if line)


def _extract_pdf(path: str) -> str:
    """
    Extract text from a PDF.

    Strategy (in order):
    1. PyMuPDF (fitz) — per-page: embedded text if present, else render page
       to a numpy image array and run EasyOCR on it.
    2. pypdf fallback — text-only, no OCR (used only when fitz is absent).
    """
    try:
        import fitz  # PyMuPDF  # noqa: PLC0415
        return _extract_pdf_fitz(path, fitz)
    except ImportError:
        return _extract_pdf_pypdf(path)


def _extract_pdf_fitz(path: str, fitz) -> str:
    """Per-page extraction: digital text or rendered-image OCR via PyMuPDF."""
    import numpy as np  # noqa: PLC0415

    doc = fitz.open(path)
    pages_text: list[str] = []
    try:
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages_text.append(text)
            else:
                # Scanned page — render at 2× zoom for better OCR accuracy.
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )
                if pix.n == 4:  # RGBA → RGB
                    img = img[:, :, :3]
                pages_text.append(_ocr_image(img))
    finally:
        doc.close()
    return "\n".join(pages_text).strip()


def _extract_pdf_pypdf(path: str) -> str:
    """Text-only extraction via pypdf (no OCR fallback)."""
    try:
        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "pypdf is required for PDF text extraction. "
            "Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
