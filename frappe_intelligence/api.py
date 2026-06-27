"""
api.py
------
Public ``@frappe.whitelist`` endpoints for the frappe_intelligence app.

This module is intentionally thin: it handles HTTP-level concerns only
(authentication, parameter validation, request dispatch, response shaping)
and delegates all business logic to the engine layer.

Other Frappe apps call these methods via::

    frappe.call("frappe_intelligence.api.process_document", file_url=..., ...)

Chat intelligence lives in ``engine/chat.py``.
Document extraction lives in ``engine/orchestrator.py``.
"""
from __future__ import annotations

import json as _json

import frappe

from frappe_intelligence.engine.chat import classify_text_intent, get_widget_roles
from frappe_intelligence.engine.orchestrator import fire_post_processors, link_log_to_record
from frappe_intelligence.utils.file_utils import resolve_file_path, validate_file_access

# Route-map cache key is local to this module (only used in get_route_map)
_ROUTE_MAP_CACHE_KEY = "fi_route_map"

# Per-user rate-limit: max calls per window, window duration in seconds.
_RATE_LIMIT_MAX = 20
_RATE_LIMIT_WINDOW = 60  # seconds

# Maximum accepted length for free-text user input.
_TEXT_INPUT_MAX_LEN = 4000


def _get_confidence_threshold(workflow_key: str | None = None) -> float:
    """Return the confidence threshold to use for this request.

    Checks the per-workflow override first (AI Workflow.confidence_threshold > 0),
    then falls back to the global AI Settings value, then to the hard default 0.6.
    """
    if workflow_key:
        try:
            wf_threshold = frappe.db.get_value(
                "AI Workflow", workflow_key, "confidence_threshold"
            )
            if wf_threshold and float(wf_threshold) > 0:
                return float(wf_threshold)
        except Exception:
            pass
    try:
        global_threshold = frappe.db.get_single_value("AI Settings", "confidence_threshold")
        return float(global_threshold) if global_threshold else 0.6
    except Exception:
        return 0.6


# ===========================================================================
# Debug / diagnostics
# ===========================================================================

@frappe.whitelist()
def debug_chat(text: str = "Hi") -> dict:
    """
    Run the full chat pipeline step-by-step and return a diagnostics report.

    Call from the browser console (no page reload needed):

        frappe.call("frappe_intelligence.api.debug_chat", {text: "Hi"})
            .then(r => console.table(r.message.steps));

    Safe to leave in production — only logged-in users can call it.
    """
    import traceback as _tb  # noqa: PLC0415

    steps: list[dict] = []

    # ── Step 1: read provider + model from AI Settings ──────────────────
    try:
        provider = frappe.db.get_single_value("AI Settings", "ai_provider") or "Ollama"
        model_key = {"Claude": "claude_model", "Gemini": "gemini_model"}.get(provider, "ollama_model")
        model = frappe.db.get_single_value("AI Settings", model_key) or "(default)"
        steps.append({"step": "config", "ok": True, "provider": provider, "model": model})
    except Exception as exc:
        steps.append({"step": "config", "ok": False, "error": str(exc)})
        return {"steps": steps}

    # ── Step 2: build adapter ────────────────────────────────────────────
    try:
        from frappe_intelligence.models.llm_factory import get_adapter  # noqa: PLC0415
        adapter = get_adapter()
        steps.append({"step": "adapter", "ok": True, "type": type(adapter).__name__})
    except Exception as exc:
        steps.append({"step": "adapter", "ok": False,
                      "error": str(exc), "trace": _tb.format_exc()})
        return {"steps": steps}

    # ── Step 3: call adapter.chat() — no tools, no history ──────────────
    try:
        reply, error = adapter.chat(text, history=[], tools=[])
        if error:
            steps.append({"step": "chat", "ok": False, "error": error})
        else:
            steps.append({"step": "chat", "ok": True,
                          "reply": (str(reply)[:500] if reply else None)})
    except Exception as exc:
        steps.append({"step": "chat", "ok": False,
                      "error": str(exc), "trace": _tb.format_exc()})

    return {"steps": steps}


def _assert_log_access(log_name: str) -> None:
    """
    Raise PermissionError if the current user is neither the owner of the
    AI Processing Log nor a System Manager.

    Used by confirm_extraction and submit_correction.  This ownership-based
    check is intentional: the AI Processing Log DocType carries no role
    permissions (it is created internally with ignore_permissions=True), so
    Frappe's standard has_permission() always returns False for non-admins.
    Instead we enforce that only the session that triggered the processing
    can act on its result.
    """
    owner = frappe.db.get_value("AI Processing Log", log_name, "owner")
    if owner is None:
        frappe.throw(
            frappe._("Processing log not found: {0}").format(log_name),
            frappe.DoesNotExistError,
        )
    if owner != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(
            frappe._("You do not have permission to access this processing log."),
            frappe.PermissionError,
        )


def _enforce_rate_limit() -> None:
    """
    Raise ``frappe.RateLimitExceededError`` when the current user has
    exceeded ``_RATE_LIMIT_MAX`` LLM calls within ``_RATE_LIMIT_WINDOW``
    seconds.  Uses Redis as a lightweight counter.
    """
    key = f"fi_rl:{frappe.session.user}"
    count = frappe.cache().get_value(key) or 0
    if count >= _RATE_LIMIT_MAX:
        frappe.throw(
            frappe._(
                "You have sent too many requests. Please wait a moment before trying again."
            ),
            frappe.RateLimitExceededError,
        )
    frappe.cache().set_value(key, count + 1, expires_in_sec=_RATE_LIMIT_WINDOW)


# ===========================================================================
# Document processing
# ===========================================================================

@frappe.whitelist()
def process_document(file_url: str, target_doctype: str | None = None) -> dict:
    """
    Enqueue document processing and return immediately.

    The heavy work (OCR + LLM extraction) runs in a background long-queue
    worker.  When complete, the result is pushed to the browser via the
    ``ai_processing_complete`` realtime event.

    Parameters
    ----------
    file_url:
        Frappe file URL (e.g. ``/files/national_address.jpg`` or
        ``/private/files/cr_scan.pdf``).
    target_doctype:
        Optional ``document_type_key`` of the expected AI Document Template.
        Pass ``None`` for automatic classification.

    Returns
    -------
    ``{"status": "queued", "log_name": str}``
    """
    _enforce_rate_limit()
    validate_file_access(file_url)

    from frappe_intelligence.engine.orchestrator import AIEngine
    log = AIEngine()._create_log(file_url)

    frappe.enqueue(
        "frappe_intelligence.engine.orchestrator.process_document_background",
        queue="long",
        timeout=600,
        log_name=log.name,
        file_url=file_url,
        target_doctype=target_doctype,
        session_user=frappe.session.user,
    )

    return {"status": "queued", "log_name": log.name}


# ===========================================================================
# Processing log status (polling fallback for realtime)
# ===========================================================================

@frappe.whitelist()
def get_log_status(log_name: str) -> dict:
    """
    Return the current status of an AI Processing Log.

    Used by the widget as a polling fallback when the socket.io realtime
    event does not arrive (dev proxies, VPN, etc.).

    Returns
    -------
    ``{"status": "Pending"|"Processing"|"Completed"|"Failed", "result": dict|None}``
    The ``result`` key mirrors the shape of the ``ai_processing_complete``
    realtime payload so the widget can call ``_handleProcessingResult`` directly.
    """
    _assert_log_access(log_name)

    log = frappe.get_doc("AI Processing Log", log_name)

    if log.processing_status not in ("Completed", "Failed"):
        return {"status": log.processing_status, "result": None}

    log_session = frappe.db.get_value("AI Processing Log", log_name, "session")
    wf_key = frappe.db.get_value("AI Agent Session", log_session, "workflow") if log_session else None
    threshold = _get_confidence_threshold(wf_key)
    confidence = float(log.confidence_score or 0.0)
    needs_review = log.processing_status == "Completed" and confidence < threshold

    result = {
        "status": "success" if log.processing_status == "Completed" else "failed",
        "document_type_key": log.document_type_key or None,
        "extracted_data": frappe.parse_json(log.extracted_data or "{}"),
        "confidence_score": confidence,
        "log_name": log_name,
        "needs_review": needs_review,
    }
    return {"status": log.processing_status, "result": result}


# ===========================================================================
# Template management
# ===========================================================================

@frappe.whitelist()
def list_templates() -> list[dict]:
    """Return all active AI Document Templates (name, key, model preference)."""
    return frappe.get_all(
        "AI Document Template",
        filters={"is_active": 1},
        fields=["name", "document_name",
                "document_type_key", "model_preference"],
        order_by="document_name asc",
    )


# ===========================================================================
# Generic document creation
# ===========================================================================

@frappe.whitelist()
def create_document(doctype: str, values: str) -> dict:
    """
    Create a Frappe document from a JSON values dict and return its name + route.

    Child table fields are detected automatically via DocType meta — any value
    that is a list is treated as child rows for that field.

    Parameters
    ----------
    doctype:
        Target DocType, e.g. ``"Sales Invoice"``.
    values:
        JSON string of ``{fieldname: value}`` pairs.  Lists are inserted as
        child rows; all other values are set directly.

    Returns
    -------
    ``{"name": str, "route": str}``
    """
    frappe.has_permission(doctype, ptype="create", throw=True)

    data: dict = _json.loads(values) if isinstance(
        values, str) else (values or {})

    meta = frappe.get_meta(doctype)
    table_fields = {
        f.fieldname
        for f in meta.fields
        if f.fieldtype in ("Table", "Table MultiSelect")
    }

    doc = frappe.new_doc(doctype)
    for key, val in data.items():
        if key in table_fields and isinstance(val, list):
            for row in val:
                doc.append(key, row)
        elif key not in table_fields:
            doc.set(key, val)

    doc.insert(ignore_permissions=False)

    doctype_slug = doctype.lower().replace(" ", "-")
    name_slug = doc.name.lower().replace(" ", "-").replace("_", "-")
    return {"name": doc.name, "route": f"/app/{doctype_slug}/{name_slug}"}


# ===========================================================================
# Widget settings & navigation
# ===========================================================================

@frappe.whitelist(allow_guest=False)
def get_widget_settings() -> dict:
    """
    Return widget appearance values, route map, and allowed roles from AI Settings.

    Called automatically by the widget on every page load.
    Provides safe defaults so the widget always renders even when AI Settings
    has never been saved.
    """
    defaults = {"widget_color": "#6c63ff", "widget_icon": "", "text_color": "",
                "assistant_name": "AI Assistant", "route_map": {}, "allowed_roles": []}
    try:
        color = frappe.db.get_single_value("AI Settings", "widget_color") or ""
        icon = frappe.db.get_single_value("AI Settings", "widget_icon") or ""
        text_color = frappe.db.get_single_value(
            "AI Settings", "text_color") or ""
        assistant_name = frappe.db.get_single_value(
            "AI Settings", "assistant_name") or "AI Assistant"
        return {
            "widget_color": color or defaults["widget_color"],
            "widget_icon": icon,
            "text_color": text_color,
            "assistant_name": assistant_name,
            "route_map": get_route_map(),
            "allowed_roles": get_widget_roles(),
        }
    except Exception:
        return defaults


@frappe.whitelist(allow_guest=False)
def get_route_map() -> dict:
    """
    Return the navigation route map from AI Settings as a plain dict.

    Cached 1 hour in Redis; cleared on every AI Settings save.

    Returns
    -------
    ``{document_type_key: {"label": str, "route": str}, ...}``
    """
    cached = frappe.cache().get_value(_ROUTE_MAP_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        rows = frappe.get_all(
            "AI Route Map",
            filters={"parent": "AI Settings", "parenttype": "AI Settings"},
            fields=["document_type_key", "label", "route"],
        )
        result = {
            r.document_type_key: {
                "label": r.label or r.document_type_key, "route": r.route}
            for r in rows
            if r.document_type_key and r.route
        }
    except Exception:
        result = {}
    frappe.cache().set_value(_ROUTE_MAP_CACHE_KEY, result, expires_in_sec=3600)
    return result


# ===========================================================================
# Training
# ===========================================================================

@frappe.whitelist()
def submit_correction(log_name: str, corrected_extraction: dict | str) -> dict:
    """
    Submit a user correction for a processed document.

    Creates an **AI Training Pair** linked to *log_name* so patterns can be
    improved over time.  Only the log owner or a System Manager may submit.

    Returns
    -------
    ``{"training_pair": "<new AI Training Pair name>"}``
    """
    _assert_log_access(log_name)

    if isinstance(corrected_extraction, str):
        corrected_extraction = _json.loads(corrected_extraction)

    log = frappe.get_doc("AI Processing Log", log_name)
    pair = frappe.new_doc("AI Training Pair")
    pair.document_template = log.document_template
    pair.processing_log = log_name
    pair.session = log.session if log.session else None
    pair.original_extraction = log.extracted_data
    pair.corrected_extraction = frappe.as_json(corrected_extraction)
    pair.correction_source = frappe.session.user
    pair.insert(ignore_permissions=True)
    return {"training_pair": pair.name}


# ===========================================================================
# Post-processors
# ===========================================================================

@frappe.whitelist()
def register_post_processor(
    document_type_key: str,
    callback_method: str,
    description: str | None = None,
) -> dict:
    """
    Register a Python callable to be enqueued after a successful extraction.

    Returns
    -------
    ``{"name": "<new AI Post Processor doc name>"}``
    """
    frappe.only_for("System Manager")
    doc = frappe.new_doc("AI Post Processor")
    doc.document_type_key = document_type_key
    doc.callback_method = callback_method
    doc.description = description or ""
    doc.is_active = 1
    doc.insert(ignore_permissions=True)
    return {"name": doc.name}


# ===========================================================================
# Connection test
# ===========================================================================

@frappe.whitelist()
def test_connection() -> dict:
    """
    Verify that the currently configured AI provider is reachable.

    Requires System Manager.

    Returns
    -------
    ``{"ok": True}`` on success, ``{"ok": False, "error": str}`` on failure.
    """
    frappe.only_for("System Manager")
    _enforce_rate_limit()
    from frappe_intelligence.models.llm_factory import get_adapter
    adapter = get_adapter()
    if hasattr(adapter, "test_connection"):
        ok, error = adapter.test_connection()
        return {"ok": ok} if not error else {"ok": False, "error": error}
    _, error = adapter.chat("Say 'ok' in one word.")
    return {"ok": True} if not error else {"ok": False, "error": error}


# ===========================================================================
# Widget context
# ===========================================================================

@frappe.whitelist()
def get_required_documents(doctype: str, docname: str) -> dict:
    """
    Return present/missing required AI document types for a Frappe record.

    Used by the widget's proactive bubble and Smart Checklist.

    Returns
    -------
    ``{"present": [...], "missing": [...]}``
    """
    if not frappe.has_permission(doctype, doc=docname, ptype="read"):
        frappe.throw(
            frappe._("You do not have permission to read this record."),
            frappe.PermissionError,
        )

    requirements = frappe.get_all(
        "AI Document Requirement",
        filters={"target_doctype": doctype, "is_active": 1},
        fields=["document_type_key", "label"],
        order_by="label asc",
    )
    if not requirements:
        return {"present": [], "missing": []}

    processed_keys = set(
        frappe.db.get_all(
            "AI Processing Log",
            filters={
                "linked_doctype": doctype,
                "linked_docname": docname,
                "processing_status": "Completed",
            },
            pluck="document_type_key",
        )
    )

    present, missing = [], []
    for req in requirements:
        entry = {"document_type_key": req.document_type_key,
                 "label": req.label or req.document_type_key}
        (present if req.document_type_key in processed_keys else missing).append(entry)

    return {"present": present, "missing": missing}


# ===========================================================================
# Chat session management
# ===========================================================================

@frappe.whitelist()
def clear_chat_history() -> dict:
    """
    Clear the current session's chat history.

    Called by the widget "New Conversation" button.
    """
    frappe.cache().delete_value(f"fi_chat:{frappe.session.sid}")
    return {"ok": True}


# ===========================================================================
# Low-confidence review confirmation
# ===========================================================================

@frappe.whitelist()
def confirm_extraction(
    log_name: str,
    doctype: str | None = None,
    docname: str | None = None,
) -> dict:
    """
    Accept a low-confidence extraction result and fire its post-processors.

    Called after the user reviews and accepts a result held below the
    confidence threshold configured in AI Settings.  Only the log owner
    or a System Manager may confirm.
    """
    _assert_log_access(log_name)

    log = frappe.get_doc("AI Processing Log", log_name)
    fire_post_processors(
        log.document_type_key,
        {"extracted_data": frappe.parse_json(
            log.extracted_data or "{}"), "log_name": log_name},
        doctype,
        docname,
    )
    return {"ok": True}


# ===========================================================================
# Unified widget input handler
# ===========================================================================

@frappe.whitelist()
def handle_widget_input(
    input_type: str,
    file_url: str | None = None,
    text_input: str | None = None,
    doctype: str | None = None,
    docname: str | None = None,
    audio_pending: int = 0,
    widget_mode: str = "global",
    chat_mode: str = "ask",
    workflow_key: str | None = None,
) -> dict:
    """
    Single entry-point for all widget input modes.

    Parameters
    ----------
    input_type:
        ``"file"``, ``"voice"``, or ``"text"``.
    file_url:
        Required for ``file`` and ``voice`` modes.
    text_input:
        Required for ``text`` mode.
    doctype, docname:
        Context hints forwarded to intent classification and post-processors.
    audio_pending:
        ``1`` = audio still uploading; return immediately with an acknowledgement.

    Returns
    -------
    * ``file``  → same shape as ``process_document``
    * ``voice`` → ``{"transcript", "reply", "action", "action_data"}``
    * ``text``  → ``{"reply", "action", "action_data"}``
    """
    if audio_pending:
        return {"status": "pending", "reply": "Upload in progress…"}

    _enforce_rate_limit()

    # ------------------------------------------------------------------ file
    if input_type == "file":
        if not file_url:
            frappe.throw(
                frappe._("file_url is required for input_type='file'."))
        assert file_url is not None  # narrow str | None → str for the type checker
        validate_file_access(file_url)

        from frappe_intelligence.engine.orchestrator import AIEngine
        result = AIEngine().process(file_url=file_url)

        if doctype and docname and result.get("log_name"):
            link_log_to_record(
                result["log_name"], doctype, docname, result.get("document_type_key"))

        threshold = _get_confidence_threshold(workflow_key)
        needs_review = (
            result.get("status") == "success" and
            result.get("confidence_score", 0.0) < threshold
        )
        result["needs_review"] = needs_review

        if not needs_review:
            fire_post_processors(result.get(
                "document_type_key"), result, doctype, docname)

        frappe.publish_realtime(
            "ai_processing_update", {"message": "Extraction complete!"}, user=frappe.session.user
        )
        return result

    # ----------------------------------------------------------------- voice
    if input_type == "voice":
        if not file_url:
            frappe.throw(
                frappe._("file_url is required for input_type='voice'."))
        assert file_url is not None  # narrow str | None → str for the type checker
        validate_file_access(file_url)

        from frappe_intelligence.models.transcriber import transcribe
        frappe.publish_realtime(
            "ai_processing_update", {"message": "Transcribing audio…"}, user=frappe.session.user
        )
        voice_lang = frappe.db.get_single_value(
            "AI Settings", "voice_language") or None
        transcript = transcribe(resolve_file_path(
            file_url), language=voice_lang)

        if transcript:
            intent = classify_text_intent(
                transcript, doctype, docname, widget_mode)
        else:
            intent = {"reply": "", "action": None, "action_data": None}
        return {
            "transcript": transcript,
            "reply": intent.get("reply", ""),
            "action": intent.get("action"),
            "action_data": intent.get("action_data"),
        }

    # ------------------------------------------------------------------ text
    if input_type == "text":
        if not text_input:
            frappe.throw(
                frappe._("text_input is required for input_type='text'."))
        assert text_input is not None  # narrow str | None → str for the type checker
        if len(text_input) > _TEXT_INPUT_MAX_LEN:
            frappe.throw(
                frappe._("Text input exceeds the maximum allowed length of {0} characters.").format(
                    _TEXT_INPUT_MAX_LEN
                ),
                frappe.ValidationError,
            )
        if chat_mode == "agent" and workflow_key:
            intent = classify_text_intent(
                text_input, doctype, docname, widget_mode,
                channel="desk", channel_id=frappe.session.sid,
                workflow_key=workflow_key,
            )
        else:
            intent = classify_text_intent(text_input, doctype, docname, widget_mode)
        return {
            "reply": intent.get("reply", ""),
            "action": intent.get("action"),
            "action_data": intent.get("action_data"),
        }

    frappe.throw(
        frappe._("Unknown input_type '{0}'. Expected: file, voice, text.").format(
            input_type)
    )
    return {}  # unreachable — frappe.throw always raises; satisfies the type checker


# ===========================================================================
# WhatsApp feature gates
# ===========================================================================

@frappe.whitelist()
def is_whatsapp_installed() -> bool:
    """True when frappe_whatsapp is installed on this site.

    Checks for the WhatsApp Settings DocType — it is created by
    frappe_whatsapp on install and removed on uninstall.
    """
    return bool(frappe.db.exists("DocType", "WhatsApp Settings"))


@frappe.whitelist()
def is_whatsapp_enabled() -> bool:
    """True when frappe_whatsapp is installed, a default incoming account
    exists, that account's status is 'Active', AND AI Settings has the
    enable_ai_on_whatsapp switch turned on.

    Called by:
      - AI Settings form JS → show/hide WhatsApp config section
      - Vue Workflow Builder → show/hide 'WhatsApp Flow' step fields
      - whatsapp_handler.py → guard before processing any incoming message
    """
    if not frappe.db.exists("DocType", "WhatsApp Settings"):
        return False
    try:
        enabled = frappe.db.get_single_value("AI Settings", "enable_ai_on_whatsapp")
        if not enabled:
            return False
        default_account = frappe.db.get_single_value(
            "WhatsApp Settings", "default_incoming_account"
        )
        if not default_account:
            return False
        status = frappe.db.get_value("WhatsApp Account", default_account, "status")
        return status == "Active"
    except Exception:
        return False


# ===========================================================================
# Workflow selector
# ===========================================================================

@frappe.whitelist()
def list_workflows() -> list[dict]:
    """Return active AI Workflow records for the Ask/Agent mode selector dropdown.

    Returns
    -------
    ``[{"workflow_key": str, "title": str}, ...]``
    """
    return frappe.get_all(
        "AI Workflow",
        filters={"is_active": 1},
        fields=["workflow_key", "title"],
        order_by="title asc",
    )


# ===========================================================================
# Workflow Plan Builder — read
# ===========================================================================

@frappe.whitelist()
def get_workflow_for_builder(workflow_key: str) -> dict:
    """
    Return the full builder payload for a given AI Workflow.

    Used by the Vue Workflow Plan Builder page to populate its state on load.
    All data is read-only — no writes are made here.

    Returns
    -------
    ``{
        "workflow":             {workflow fields},
        "steps":                [{step fields}, ...],
        "requirements":         [{requirement fields}, ...],
        "knowledge_packs":      [],          # reserved — no assignment table yet
        "post_processors":      [],          # reserved — no assignment table yet
        "available_templates":  [{name, document_type_key, document_name}, ...],
        "available_packs":      [{name, pack_name, description, is_active}, ...],
        "available_processors": [{name, callback_method, description, is_active}, ...],
        "available_wa_flows":   [{name}, ...] or [] when frappe_whatsapp absent
    }``
    """
    frappe.only_for("System Manager")

    wf = frappe.get_doc("AI Workflow", workflow_key)

    steps = [
        {
            "step_order":      s.step_order,
            "step_key":        s.step_key,
            "prompt_to_user":  s.prompt_to_user,
            "target_doctype":  s.target_doctype,
            "whatsapp_flow":   s.whatsapp_flow,
            "required_fields": s.required_fields,
            "completion_check": s.completion_check,
            "next_step_key":   s.next_step_key,
        }
        for s in (wf.steps or [])
    ]

    requirements = frappe.get_all(
        "AI Document Requirement",
        filters={"workflow": workflow_key},
        fields=["name", "target_doctype", "document_type_key",
                "label", "step_key", "is_active"],
        order_by="step_key asc, label asc",
    )

    available_templates = frappe.get_all(
        "AI Document Template",
        filters={"is_active": 1},
        fields=["name", "document_type_key", "document_name", "model_preference"],
        order_by="document_name asc",
    )

    available_packs = frappe.get_all(
        "AI Knowledge Pack",
        fields=["name", "pack_name", "description", "is_active"],
        order_by="pack_name asc",
    )

    available_processors = frappe.get_all(
        "AI Post Processor",
        filters={"is_active": 1},
        fields=["name", "callback_method", "description", "document_type_key"],
        order_by="callback_method asc",
    )

    # WhatsApp Flows — only available when frappe_whatsapp is installed.
    available_wa_flows: list[dict] = []
    if frappe.db.exists("DocType", "WhatsApp Flow"):
        available_wa_flows = frappe.get_all(
            "WhatsApp Flow",
            fields=["name"],
            order_by="name asc",
        )

    knowledge_packs = [
        {"pack": row.pack}
        for row in (wf.knowledge_packs or [])
    ]

    processor_assignments = [
        {"step_key": row.step_key, "processor": row.processor}
        for row in (wf.post_processors or [])
    ]

    return {
        "workflow": {
            "workflow_key":       wf.workflow_key,
            "title":              wf.title,
            "is_active":          wf.is_active,
            "allow_desk":         wf.allow_desk,
            "allow_portal":       wf.allow_portal,
            "allow_whatsapp":     wf.allow_whatsapp,
            "scope_description":  wf.scope_description,
            "out_of_scope_reply": wf.out_of_scope_reply,
        },
        "steps":                steps,
        "requirements":         requirements,
        "knowledge_packs":      knowledge_packs,
        "processor_assignments": processor_assignments,
        "available_templates":  available_templates,
        "available_packs":      available_packs,
        "available_processors": available_processors,
        "available_wa_flows":   available_wa_flows,
    }


# ===========================================================================
# Workflow Plan Builder — write
# ===========================================================================

@frappe.whitelist()
def save_workflow_builder(workflow_key: str, payload: dict | str) -> dict:
    """
    Atomically upsert an AI Workflow from the Vue builder payload.

    Persists:
      - AI Workflow header fields (title, is_active, channels, scope, out_of_scope_reply)
      - AI Workflow Step children (full replace — order, key, prompt, doctype, fields, etc.)
      - AI Document Requirement records (sync: create missing, delete removed)
      - Knowledge Pack assignments (``knowledge_packs`` child table, full replace)
      - Step Post-Processor assignments (``post_processors`` child table, full replace)

    Parameters
    ----------
    workflow_key:
        Identifies the AI Workflow to update. Must already exist.
    payload:
        JSON with keys: ``workflow``, ``steps``, ``requirements``,
        ``knowledge_packs``, ``processor_assignments``.

    Returns
    -------
    ``{"ok": True}``
    """
    frappe.only_for("System Manager")

    if isinstance(payload, str):
        import json as _json
        payload = _json.loads(payload)

    wf_data: dict = payload.get("workflow", {})
    steps_data: list[dict] = payload.get("steps", [])
    req_data: list[dict] = payload.get("requirements", [])
    packs_data: list[dict] = payload.get("knowledge_packs", [])
    processors_data: list[dict] = payload.get("processor_assignments", [])

    # --- Update AI Workflow header + steps (atomic via frappe.get_doc + save) ---
    wf = frappe.get_doc("AI Workflow", workflow_key)

    if wf_data.get("title"):
        wf.title = wf_data["title"]
    wf.is_active          = int(wf_data.get("is_active", wf.is_active))
    wf.allow_desk         = int(wf_data.get("allow_desk", wf.allow_desk))
    wf.allow_portal       = int(wf_data.get("allow_portal", wf.allow_portal))
    wf.allow_whatsapp     = int(wf_data.get("allow_whatsapp", wf.allow_whatsapp))
    wf.scope_description  = wf_data.get("scope_description", wf.scope_description)
    wf.out_of_scope_reply = wf_data.get("out_of_scope_reply", wf.out_of_scope_reply)

    # Full replace of steps child table.
    wf.steps = []
    for s in steps_data:
        wf.append("steps", {
            "step_order":      s.get("step_order", 0),
            "step_key":        s.get("step_key", ""),
            "prompt_to_user":  s.get("prompt_to_user", ""),
            "target_doctype":  s.get("target_doctype"),
            "whatsapp_flow":   s.get("whatsapp_flow"),
            "required_fields": s.get("required_fields"),
            "completion_check": s.get("completion_check"),
            "next_step_key":   s.get("next_step_key"),
        })

    # Full replace of knowledge_packs child table.
    wf.knowledge_packs = []
    for p in packs_data:
        if p.get("pack"):
            wf.append("knowledge_packs", {"pack": p["pack"]})

    # Full replace of post_processors child table.
    wf.post_processors = []
    for a in processors_data:
        if a.get("step_key") and a.get("processor"):
            wf.append("post_processors", {
                "step_key": a["step_key"],
                "processor": a["processor"],
            })

    wf.save(ignore_permissions=True)

    # --- Sync AI Document Requirement records ---
    _sync_requirements(workflow_key, req_data)

    frappe.db.commit()
    return {"ok": True}


def _sync_requirements(workflow_key: str, req_data: list[dict]) -> None:
    """Create / update / delete AI Document Requirement records for a workflow."""
    existing = {
        r.name: r
        for r in frappe.get_all(
            "AI Document Requirement",
            filters={"workflow": workflow_key},
            fields=["name", "document_type_key", "step_key"],
        )
    }

    incoming_names: set[str] = set()

    for req in req_data:
        name = req.get("name")
        if name and frappe.db.exists("AI Document Requirement", name):
            # Update existing record
            doc = frappe.get_doc("AI Document Requirement", name)
            doc.target_doctype      = req.get("target_doctype", doc.target_doctype)
            doc.document_type_key   = req.get("document_type_key", doc.document_type_key)
            doc.label               = req.get("label", doc.label)
            doc.step_key            = req.get("step_key", doc.step_key)
            doc.is_active           = int(req.get("is_active", doc.is_active))
            doc.save(ignore_permissions=True)
            incoming_names.add(name)
        else:
            # Create new record
            doc = frappe.new_doc("AI Document Requirement")
            doc.workflow          = workflow_key
            doc.target_doctype    = req.get("target_doctype", "")
            doc.document_type_key = req.get("document_type_key", "")
            doc.label             = req.get("label", "")
            doc.step_key          = req.get("step_key", "")
            doc.is_active         = int(req.get("is_active", 1))
            doc.insert(ignore_permissions=True)
            incoming_names.add(doc.name)

    # Delete requirements no longer in the payload
    for name in existing:
        if name not in incoming_names:
            frappe.delete_doc("AI Document Requirement", name, ignore_permissions=True)


# ===========================================================================
# Workflow Plan Builder — prompt preview
# ===========================================================================

@frappe.whitelist()
def preview_step_prompt(step_data: dict | str) -> dict:
    """
    Return the rendered LLM prompt for an unsaved step draft.

    The Vue builder calls this as the user edits a step, debounced at 500 ms.
    ``step_data`` contains the same fields as an AI Workflow Step child row but
    may be partially filled (unsaved draft state).

    Parameters
    ----------
    step_data:
        Dict with step fields (step_key, prompt_to_user, required_fields, …).

    Returns
    -------
    ``{"prompt": str}``
    """
    frappe.only_for("System Manager")

    if isinstance(step_data, str):
        import json as _json
        step_data = _json.loads(step_data)

    from frappe_intelligence.engine.workflow import build_step_prompt

    # Build a lightweight mock step object that build_step_prompt can consume.
    class _MockStep:
        def __init__(self, data: dict):
            self.step_key        = data.get("step_key", "")
            self.prompt_to_user  = data.get("prompt_to_user", "")
            self.required_fields = data.get("required_fields")
            self.target_doctype  = data.get("target_doctype")

    mock_step = _MockStep(step_data)
    prompt = build_step_prompt(mock_step, collected_so_far={}, workflow_doc=None)
    return {"prompt": prompt}
