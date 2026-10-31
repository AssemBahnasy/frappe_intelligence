"""WhatsApp channel bridge for frappe_intelligence.

Entry point: on_whatsapp_message(doc, method)
  Registered via doc_events["WhatsApp Message"]["after_insert"] in hooks.py.
  Called by Frappe after frappe_whatsapp creates every inbound WhatsApp Message.

Architecture constraint
-----------------------
`on_whatsapp_message` does exactly ONE thing: enqueue and return.
Meta's webhook expects a response within 5 seconds. Any LLM call here
will timeout, causing Meta to retry → duplicate AI sessions.
All heavy work runs in the RQ background job.
"""
from __future__ import annotations

import frappe
from frappe.utils import now_datetime

# ---------------------------------------------------------------------------
# Rate-limit constants — 10 messages per phone per 60 seconds
# ---------------------------------------------------------------------------

_WA_RATE_LIMIT_MAX = 10
_WA_RATE_LIMIT_WINDOW = 60  # seconds


class _WAUserRateLimitError(Exception):
    """Raised inside the background job; caught silently (no error reply)."""
    pass


# ---------------------------------------------------------------------------
# Entry hook — synchronous, must return in < 5 s
# ---------------------------------------------------------------------------

def on_whatsapp_message(doc, method=None):
    """Frappe doc_event hook — fires after every WhatsApp Message insert.

    Three guards then enqueue-only. Never touches LLM.
    """
    # Guard 1: skip non-incoming messages (our own outgoing replies, etc.)
    if doc.get("type") != "Incoming":
        return

    # Guard 2: skip if WhatsApp AI processing is not enabled on this site
    if not _is_whatsapp_enabled():
        return

    # Guard 3: deduplicate — Meta can deliver the same webhook event twice
    message_id = doc.get("message_id") or doc.name
    if _is_already_processing(message_id):
        return

    phone = _normalize_phone(doc.get("from") or "")
    if not phone:
        return

    frappe.enqueue(
        "frappe_intelligence.channels.whatsapp.process_whatsapp_message_job",
        queue="default",
        timeout=300,
        message_name=doc.name,
        phone=phone,
        whatsapp_account=doc.whatsapp_account,
        message_id=message_id,
    )


# ---------------------------------------------------------------------------
# Background job — all LLM work happens here
# ---------------------------------------------------------------------------

def process_whatsapp_message_job(
    message_name: str,
    phone: str,
    whatsapp_account: str,
    message_id: str,
) -> None:
    """RQ background job.  Routes incoming WhatsApp Message by content_type."""
    from frappe_intelligence.workflows import sessions

    try:
        doc = frappe.get_doc("WhatsApp Message", message_name)

        # Touch session so last_user_message_at is always current
        workflow_key = _get_whatsapp_workflow_key()
        session = sessions.session("WhatsApp", phone, workflow_key)
        session.last_user_message_at = now_datetime()
        session.save(ignore_permissions=True)

        # Per-phone rate limit (raises _WAUserRateLimitError when exceeded)
        _enforce_wa_rate_limit(phone)

        content_type = (doc.content_type or "text").strip().lower()

        if content_type == "text":
            text = (doc.message or "").strip()
            if text:
                process_whatsapp_text(session, text, doc)

        elif content_type == "flow":
            handle_flow_response(session, doc)

        elif content_type == "audio":
            _handle_audio(session, doc, phone, whatsapp_account)

        elif content_type in ("image", "document"):
            _handle_media(doc)

        elif content_type == "button":
            # Button payloads are treated as free text
            text = (doc.get("button_payload") or doc.message or "").strip()
            if text:
                process_whatsapp_text(session, text, doc)

        else:
            # Unknown type — fall through to text if any content available
            text = (doc.message or "").strip()
            if text:
                process_whatsapp_text(session, text, doc)

    except _WAUserRateLimitError:
        # Expected behaviour — do not send error reply; just drop silently
        return

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "whatsapp_handler.process_whatsapp_message_job",
        )
        _send_error_reply(phone, whatsapp_account, message_id)


# ---------------------------------------------------------------------------
# Text processing — scope check + step runner + LLM
# ---------------------------------------------------------------------------

def process_whatsapp_text(session, text: str, incoming_msg) -> None:
    """Run text through the workflow engine and send the AI reply.

    Delegates to workflows.sessions.reply, which handles:
    scope enforcement, step-driven prompt building, LLM call, turn persistence.
    """
    if not _within_24h_window(session):
        # Outside Meta's 24-hour free-message window — cannot send free-form.
        # Silently skip rather than attempting a message Meta will reject.
        return

    from frappe_intelligence.workflows import sessions

    workflow_key = session.workflow or _get_whatsapp_workflow_key()
    result = sessions.reply(text, "WhatsApp", session.channel_id, workflow_key)

    reply = result.get("reply") or ""
    if reply:
        _send_whatsapp_reply(
            to=session.channel_id,
            message=reply,
            whatsapp_account=incoming_msg.whatsapp_account,
            reply_to_id=incoming_msg.name,
        )


# ---------------------------------------------------------------------------
# Flow response — structured WhatsApp Flow data collection
# ---------------------------------------------------------------------------

def handle_flow_response(session, incoming_msg) -> None:
    """Store a completed WhatsApp Flow's values on the current step and send the next question.

    The flow's field names must match the step's Required Fields keys.
    """
    from frappe_intelligence.workflows import steps, turn

    flow_data = frappe.parse_json(incoming_msg.get("flow_response") or "{}")
    workflow = frappe.get_doc("AI Workflow", session.workflow) if session.workflow else None
    step = steps.current(session, workflow) if workflow else None
    if not step or not isinstance(flow_data, dict):
        return

    steps.collect(session, step, flow_data)
    complete = not steps.missing(session, step)
    refusal = steps.refused(session, step) if complete else None
    if complete and not refusal:
        step = steps.advance(session, workflow)
    if step:
        message = " ".join(filter(None, [refusal, turn.question(session, step)]))
    else:
        message = workflow.completion_message or frappe._("Thank you! Your request has been submitted.")
    session.add_fixed_reply(message)
    session.save(ignore_permissions=True)
    _send_whatsapp_reply(
        to=session.channel_id,
        message=message,
        whatsapp_account=incoming_msg.whatsapp_account,
        reply_to_id=incoming_msg.name,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _handle_audio(session, doc, phone: str, whatsapp_account: str) -> None:
    """Transcribe audio and route as text."""
    try:
        from frappe_intelligence.documents.transcriber import transcribe
        from frappe_intelligence.utils.file_utils import resolve_file_path
    except ImportError:
        return

    file_path = resolve_file_path(doc.attach or "")
    voice_lang = frappe.db.get_single_value("AI Settings", "voice_language") or None
    text = (transcribe(file_path, language=voice_lang) or "").strip()
    if text:
        process_whatsapp_text(session, text, doc)
    else:
        _send_whatsapp_reply(
            to=phone,
            message="Sorry, I could not understand the audio message. Please try again in text.",
            whatsapp_account=whatsapp_account,
            reply_to_id=doc.name,
        )


def _handle_media(doc) -> None:
    """Fire async document extraction on an image or document attachment."""
    try:
        from frappe_intelligence.documents.pipeline import AIEngine
    except ImportError:
        return
    if doc.attach:
        AIEngine().process(file_url=doc.attach)


def _is_whatsapp_enabled() -> bool:
    """True when frappe_whatsapp is installed and AI WhatsApp processing is active.

    Checks:
      1. frappe_whatsapp app is installed (WhatsApp Settings DocType exists)
      2. AI Settings.enable_ai_on_whatsapp is checked (graceful if field absent — S9 adds it)
    """
    if not frappe.db.exists("DocType", "WhatsApp Settings"):
        return False
    try:
        enabled = frappe.db.get_single_value("AI Settings", "enable_ai_on_whatsapp")
        if enabled is not None:
            return bool(enabled)
    except Exception:
        pass
    # Field not yet present (pre-S9) — allow through so the handler works as soon
    # as frappe_whatsapp is installed; S9 will add the explicit opt-in switch.
    return True


def _is_already_processing(message_id: str) -> bool:
    """Redis dedup lock — 5-minute TTL prevents double-processing a message_id."""
    key = f"fi_wa_proc:{message_id}"
    if frappe.cache().get_value(key):
        return True
    frappe.cache().set_value(key, 1, expires_in_sec=300)
    return False


def _normalize_phone(raw: str) -> str:
    """Strip leading + and whitespace. Returns the number as Meta sends it."""
    return (raw or "").strip().lstrip("+").strip()


def _enforce_wa_rate_limit(phone: str) -> None:
    """Raise _WAUserRateLimitError when phone exceeds 10 messages in 60 seconds."""
    key = f"fi_rl_wa:{phone}"
    count = frappe.cache().get_value(key) or 0
    if count >= _WA_RATE_LIMIT_MAX:
        raise _WAUserRateLimitError(phone)
    frappe.cache().set_value(key, count + 1, expires_in_sec=_WA_RATE_LIMIT_WINDOW)


def _within_24h_window(session) -> bool:
    """True if the last user message was within Meta's 24-hour free-message window."""
    if not session.last_user_message_at:
        return False
    delta = now_datetime() - session.last_user_message_at
    return delta.total_seconds() < 86400


def _get_whatsapp_workflow_key() -> str | None:
    """Read whatsapp_workflow from AI Settings. Graceful if field absent (pre-S9)."""
    try:
        return frappe.db.get_single_value("AI Settings", "whatsapp_workflow") or None
    except Exception:
        return None


def _send_whatsapp_reply(
    to: str,
    message: str,
    whatsapp_account: str,
    reply_to_id: str | None = None,
) -> None:
    """Send one or more outgoing WhatsApp Messages.

    Splits long replies at whatsapp_max_reply_chars (configurable in AI Settings).
    frappe_whatsapp.before_insert() handles the actual Meta API POST.
    """
    try:
        max_chars = int(
            frappe.db.get_single_value("AI Settings", "whatsapp_max_reply_chars") or 1000
        )
    except Exception:
        max_chars = 1000

    chunks = _split_message(message, max_chars)
    for i, chunk in enumerate(chunks):
        doc_data = {
            "doctype": "WhatsApp Message",
            "type": "Outgoing",
            "to": to,
            "content_type": "text",
            "message": chunk,
            "whatsapp_account": whatsapp_account,
        }
        # Only mark the first chunk as a reply; subsequent ones are standalone
        if reply_to_id and i == 0:
            doc_data["is_reply"] = 1
            doc_data["reply_to_message_id"] = reply_to_id

        frappe.get_doc(doc_data).insert(ignore_permissions=True)


def _split_message(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most max_chars, breaking on word boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        # Find the last space at or before max_chars
        cut = text.rfind(" ", 0, max_chars)
        if cut == -1:
            cut = max_chars  # No space found — hard cut
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()

    return [c for c in chunks if c]


def _send_error_reply(phone: str, whatsapp_account: str, reply_to_id: str | None) -> None:
    """Send a plain-text apology when an unexpected exception occurs."""
    try:
        _send_whatsapp_reply(
            to=phone,
            message="Sorry, something went wrong on our end. Please try again in a moment.",
            whatsapp_account=whatsapp_account,
            reply_to_id=reply_to_id,
        )
    except Exception:
        # If even the error reply fails, log and give up — do not loop
        frappe.log_error(frappe.get_traceback(), "whatsapp_handler._send_error_reply")
