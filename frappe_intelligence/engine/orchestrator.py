"""
orchestrator.py
---------------
The AIEngine class is the single entry-point for document intelligence.

Flow
----
1.  Read the file (OCR via EasyOCR or text extraction).
2.  Classify the document by matching detection keywords against the
    raw text (or against the optional *target_doctype* hint).
3.  Select the matching AI Document Template.
4.  Route to the appropriate adapter: Heuristic (regex) or VLM (Ollama).
5.  Persist an AI Processing Log and return the extracted payload.

All adapters live in ``frappe_intelligence/models/`` and expose a
uniform ``extract(raw_text, rules) -> dict`` interface.

Async processing
----------------
``process_document_background`` is enqueued by ``api.process_document``
so the HTTP request returns immediately.  The background job runs the
full pipeline and pushes the result to the browser via
``frappe.publish_realtime("ai_processing_complete", ...)``.
"""
from __future__ import annotations

import traceback
from typing import Any

import frappe


class AIEngine:
    """Orchestrates the full document-intelligence pipeline."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, file_url: str, target_doctype: str | None = None) -> dict[str, Any]:
        """
        Create a new Processing Log and run the full pipeline synchronously.

        Kept for internal callers (e.g. tests, bench console).
        HTTP requests should use the background path via api.process_document.
        """
        log = self._create_log(file_url)
        return self._run_pipeline(log, file_url, target_doctype)

    def process_from_log(self, log_name: str, file_url: str, target_doctype: str | None = None) -> dict[str, Any]:
        """
        Run the pipeline on an already-created Processing Log.

        Used by ``process_document_background`` so the background worker
        can pick up a log that was committed before the job was enqueued.
        """
        log = frappe.get_doc("AI Processing Log", log_name)
        return self._run_pipeline(log, file_url, target_doctype)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self, log, file_url: str, target_doctype: str | None) -> dict[str, Any]:
        """
        Run OCR → classify → extract → persist and return the result dict.

        Parameters
        ----------
        log:
            An AI Processing Log doc (already inserted and committed).
        file_url:
            Frappe file URL of the document to process.
        target_doctype:
            Optional ``document_type_key`` hint; skips auto-classification.

        Returns
        -------
        dict with keys: status, document_type_key, extracted_data,
                        confidence_score, log_name.
        """
        try:
            raw_text = self._read_file(file_url)
            log.raw_text = raw_text
            log.processing_status = "Processing"
            log.save(ignore_permissions=True)

            template = self._classify(raw_text, target_doctype)
            if not template:
                raise ValueError(
                    f"No AI Document Template matched the document. "
                    f"(target_doctype={target_doctype!r})"
                )

            log.document_template = template.name
            extracted, confidence = self._extract(raw_text, template)

            log.extracted_data = frappe.as_json(extracted)
            log.confidence_score = confidence
            log.processing_status = "Completed"
            log.save(ignore_permissions=True)

            return {
                "status": "success",
                "document_type_key": template.document_type_key,
                "extracted_data": extracted,
                "confidence_score": confidence,
                "log_name": log.name,
            }

        except Exception as exc:
            tb = traceback.format_exc()
            frappe.log_error(title="AI Processing failed", message=tb)
            log.processing_status = "Failed"
            log.error_message = f"{type(exc).__name__}: {exc}"
            log.save(ignore_permissions=True)
            return {
                "status": "failed",
                "document_type_key": None,
                "extracted_data": {},
                "confidence_score": 0.0,
                "log_name": log.name,
            }

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _create_log(self, file_url: str):
        log = frappe.new_doc("AI Processing Log")
        log.file_url = file_url
        log.processing_status = "Pending"
        log.insert(ignore_permissions=True)
        frappe.db.commit()
        return log

    def _read_file(self, file_url: str) -> str:
        from frappe_intelligence.models.reader import read_file_text
        return read_file_text(file_url)

    def _classify(self, raw_text: str, target_doctype: str | None) -> Any | None:
        """
        Return the best-matching AI Document Template doc or None.

        When *target_doctype* is given it is tried first; the keyword
        scorer is used as a fallback / confirmation.
        """
        if target_doctype:
            doc = frappe.db.get_value(
                "AI Document Template",
                {"document_type_key": target_doctype, "is_active": 1},
                "*",
                as_dict=True,
            )
            if doc:
                return frappe.get_doc("AI Document Template", doc.name)

        templates = frappe.get_all(
            "AI Document Template",
            filters={"is_active": 1},
            fields=["name", "document_type_key", "detection_keywords"],
        )

        text_lower = raw_text.lower()
        best_match = None
        best_score = 0

        for t in templates:
            if not t.detection_keywords:
                continue
            keywords = [kw.strip().lower()
                        for kw in t.detection_keywords.split(",") if kw.strip()]
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_match = t

        if best_match:
            return frappe.get_doc("AI Document Template", best_match.name)
        return None

    def _extract(self, raw_text: str, template) -> tuple[dict, float]:
        """Dispatch to the correct adapter based on template.model_preference."""
        preference = (template.model_preference or "Heuristic").strip()

        if preference == "Heuristic":
            return self._run_heuristic(raw_text, template)
        if preference == "VLM":
            return self._run_vlm(raw_text, template)
        # "Both" — run heuristic first, fill gaps with VLM
        h_result, h_conf = self._run_heuristic(raw_text, template)
        missing_rules = [
            r for r in template.extraction_rules if not h_result.get(r.field_key)
        ]
        if missing_rules:
            v_result, v_conf = self._run_vlm(raw_text, template, rules=missing_rules)
            h_result.update(v_result)
            return h_result, (h_conf + v_conf) / 2
        return h_result, h_conf

    def _run_heuristic(self, raw_text: str, template, rules=None) -> tuple[dict, float]:
        from frappe_intelligence.models.heuristic_adapter import HeuristicAdapter
        return HeuristicAdapter().extract(raw_text, rules or template.extraction_rules)

    def _run_vlm(self, raw_text: str, template, rules=None) -> tuple[dict, float]:
        from frappe_intelligence.models.llm_factory import get_adapter
        return get_adapter().extract(raw_text, rules or template.extraction_rules)


# ===========================================================================
# Background job entry-point
# (enqueued by api.process_document — runs in a long-queue worker)
# ===========================================================================

def process_document_background(
    log_name: str,
    file_url: str,
    target_doctype: str | None,
    session_user: str,
) -> None:
    """
    Background worker: run the full pipeline on an existing Processing Log
    and push the result to the triggering user via realtime.

    Enqueued by ``frappe_intelligence.api.process_document``.
    The HTTP request creates the log and returns immediately; this function
    does the heavy lifting (OCR + LLM) asynchronously.
    """
    try:
        result = AIEngine().process_from_log(log_name, file_url, target_doctype)

        threshold = float(
            frappe.db.get_single_value("AI Settings", "confidence_threshold") or 0.6
        )
        needs_review = (
            result.get("status") == "success"
            and result.get("confidence_score", 0.0) < threshold
        )
        result["needs_review"] = needs_review

        if not needs_review:
            fire_post_processors(result.get("document_type_key"), result, None, None)

    except Exception:
        frappe.log_error(title="AI Background Processing failed", message=frappe.get_traceback())
        result = {
            "status": "failed",
            "document_type_key": None,
            "extracted_data": {},
            "confidence_score": 0.0,
            "log_name": log_name,
            "needs_review": False,
        }

    frappe.publish_realtime("ai_processing_complete", result, user=session_user)


# ===========================================================================
# Post-extraction pipeline helpers
# ===========================================================================

def _is_safe_callback(method: str) -> bool:
    """
    Return True only when *method* is a dotted path whose top-level
    package is an installed Frappe app.

    This prevents a System Manager from registering arbitrary Python
    callables (e.g. ``os.system``, ``subprocess.check_output``) as
    post-processor callbacks.
    """
    if not method or not isinstance(method, str):
        return False
    parts = method.split(".")
    if len(parts) < 2 or any(p == "" for p in parts):
        return False
    return parts[0] in frappe.get_installed_apps()


def fire_post_processors(
    document_type_key: str | None,
    extraction_result: dict,
    doctype: str | None,
    docname: str | None,
) -> None:
    """
    Enqueue all active AI Post Processors for *document_type_key*.

    Only callbacks whose top-level package is an installed Frappe app
    are accepted; others are skipped and logged.
    """
    if not document_type_key:
        return
    for method in frappe.get_all(
        "AI Post Processor",
        filters={"document_type_key": document_type_key, "is_active": 1},
        pluck="callback_method",
    ):
        if not _is_safe_callback(method):
            frappe.log_error(
                title=f"AI Post-Processor blocked: unsafe callback '{method}'",
                message=(
                    "The callback_method must be a dotted Python path whose "
                    "top-level package is an installed Frappe app. "
                    f"Received: {method!r}"
                ),
            )
            continue
        try:
            frappe.enqueue(
                method,
                queue="default",
                enqueue_after_commit=True,
                extraction_result=extraction_result,
                doctype=doctype,
                docname=docname,
            )
        except Exception:  # noqa: BLE001
            frappe.log_error(
                title=f"AI Post-Processor enqueue failed: {method}",
                message=frappe.get_traceback(),
            )


def link_log_to_record(
    log_name: str,
    doctype: str,
    docname: str,
    document_type_key: str | None,
) -> None:
    """
    Update an AI Processing Log with the Frappe record it was triggered from.

    Best-effort: failures are logged but never surfaced to the caller.
    """
    try:
        frappe.db.set_value(
            "AI Processing Log",
            log_name,
            {
                "linked_doctype": doctype,
                "linked_docname": docname,
                "document_type_key": document_type_key or "",
            },
            update_modified=False,
        )
    except Exception:  # noqa: BLE001
        frappe.log_error(
            title="AI Log link failed",
            message=frappe.get_traceback(),
        )
