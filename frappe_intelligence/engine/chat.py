"""
engine/chat.py
--------------
Chat intelligence pipeline for the Intelligence Concierge widget.

Concerns handled here
---------------------
* Multi-turn chat history   — Redis (desk) or AI Agent Session DocType (workflow mode)
* Language detection        — script analysis + allowed-language enforcement
* Knowledge retrieval (RAG) — keyword scoring over AI Knowledge Pack entries
* Frappe action tools       — FRAPPE_TOOLS schema + execute_tool dispatcher
* Intent classification     — main entry point called by api.py endpoints
* Location query fast-path  — geo-coordinates from past AI Processing Logs
* Scope enforcement         — pre-LLM gate via engine/scope.py
* Workflow step machine     — session + step tracking via engine/workflow.py
"""
from __future__ import annotations

import json as _json

import frappe

# ---------------------------------------------------------------------------
# Redis cache keys
# (imported by ai_settings.py for cache-busting on every save)
# ---------------------------------------------------------------------------

_LANG_CACHE_KEY = "fi_response_languages"
_WIDGET_ROLES_CACHE_KEY = "fi_widget_roles"

# ---------------------------------------------------------------------------
# Chat history constants
# ---------------------------------------------------------------------------

_CHAT_HISTORY_TTL = 7200    # seconds (2 h per session)
_CHAT_HISTORY_MAX = 20      # messages (10 user/assistant exchanges)
_CHAT_CONTENT_LIMIT = 2000  # chars stored per message

# seconds (5 min — short enough to pick up schema changes)
_SCHEMA_CACHE_TTL = 300
# Only fields that help the LLM reason about creation/editing.
# Required fields always included; others capped at this limit.
_SCHEMA_FIELD_LIMIT = 12
# Field types that carry actionable information for the LLM.
# Pure layout / presentational types are excluded.
_SCHEMA_USEFUL_TYPES = frozenset({
    "Link", "Dynamic Link", "Select", "Date", "Datetime",
    "Currency", "Float", "Int", "Check", "Table",
    "Data", "Small Text",
})
_SCHEMA_SKIP_TYPES = frozenset({
    "Section Break", "Column Break", "Tab Break",
    "HTML", "Button", "Fold", "Image", "Heading",
    "Text Editor", "Code", "Attach", "Attach Image",
    "Geolocation", "Signature", "Color", "Barcode",
})

# ---------------------------------------------------------------------------
# Frappe action tools
# Passed to every chat() call so the model can trigger UI actions.
# ---------------------------------------------------------------------------

FRAPPE_TOOLS = [
    {
        "name": "navigate",
        "description": (
            "Navigate the user to a specific Frappe route (page, list view, or dashboard). "
            "Use when the user asks to go somewhere or open a section of the system."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "route": {
                    "type": "string",
                    "description": "Frappe URL path, e.g. /app/customer or /app/purchase-invoice/new",
                },
                "label": {
                    "type": "string",
                    "description": "Human-readable destination label shown to the user",
                },
            },
            "required": ["route"],
        },
    },
    {
        "name": "search_records",
        "description": (
            "Search for records in a Frappe DocType by name and display the results to the user. "
            "Use when the user wants to find a specific record."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctype": {
                    "type": "string",
                    "description": "Frappe DocType to search (e.g. Customer, Supplier, Purchase Order)",
                },
                "query": {
                    "type": "string",
                    "description": "Text to search for in record names",
                },
            },
            "required": ["doctype", "query"],
        },
    },
    {
        "name": "open_record",
        "description": "Open a specific Frappe record in its form view.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctype": {"type": "string", "description": "Frappe DocType name"},
                "docname": {"type": "string", "description": "Record name or ID"},
            },
            "required": ["doctype", "docname"],
        },
    },
    {
        "name": "create_record",
        "description": (
            "Open the new-record creation form for a Frappe DocType, "
            "pre-filling any field values the user explicitly provided. "
            "Always populate 'defaults' with every value mentioned — customer, "
            "date, currency, items (array of {item_code, qty, rate}), etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctype": {
                    "type": "string",
                    "description": "Frappe DocType to create a new record for",
                },
                "defaults": {
                    "type": "object",
                    "description": (
                        "Field values to pre-fill. Use Frappe field names "
                        "(e.g. customer, posting_date). For child tables pass "
                        "an array, e.g. items: [{item_code, qty, rate}]."
                    ),
                },
            },
            "required": ["doctype"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool-need heuristic — skip FRAPPE_TOOLS for plain conversational messages.
# Gemini/Ollama adds ~300-500ms to every request when tools are present because
# the model must evaluate all function signatures before replying.
# Only attach tools when the message contains an action-oriented keyword.
# ---------------------------------------------------------------------------

_ACTION_WORDS = (
    # English
    "go to", "navigate", "open", "show me", "take me to", "create", "new ",
    "search", "find", "look for", "list all", "view all", "where is",
    # Arabic
    "انتقل", "اذهب", "افتح", "أنشئ", "ابحث", "اعرض", "أظهر", "اعثر",
    "عرض", "إنشاء", "بحث", "سجل",
)


def _needs_tools(text: str) -> bool:
    """Return True only when the message looks like a navigation/action request."""
    t = text.lower()
    return any(kw in t for kw in _ACTION_WORDS)


# Location keywords that bypass the LLM and look up geo data directly
_LOCATION_PATTERNS = (
    "أين موقع", "إحداثيات", "الموقع على الخريطة", "خريطة",
    "where is", "location", "coordinates", "map", "latitude", "longitude",
)


# ===========================================================================
# Chat history
# ===========================================================================

def get_chat_history() -> list[dict]:
    """Return the current session's chat history from Redis."""
    key = f"fi_chat:{frappe.session.sid}"
    return frappe.cache().get_value(key) or []


def append_to_chat_history(role: str, content: str) -> None:
    """Append one turn to the session history, capping at _CHAT_HISTORY_MAX."""
    key = f"fi_chat:{frappe.session.sid}"
    history = frappe.cache().get_value(key) or []
    history.append({"role": role, "content": content[:_CHAT_CONTENT_LIMIT]})
    if len(history) > _CHAT_HISTORY_MAX:
        history = history[-_CHAT_HISTORY_MAX:]
    frappe.cache().set_value(key, history, expires_in_sec=_CHAT_HISTORY_TTL)


# ===========================================================================
# Language detection and enforcement
# ===========================================================================

def get_allowed_languages() -> list[tuple[str, str]]:
    """
    Return ``[(code, name), ...]`` from the AI Response Language child table.

    Cached 1 hour in Redis; busted by ``AISettings.on_update()``.
    Empty list means the AI mirrors the user's input language (auto-detect).
    """
    cached = frappe.cache().get_value(_LANG_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        codes = frappe.get_all(
            "AI Response Language",
            filters={"parent": "AI Settings", "parenttype": "AI Settings"},
            pluck="language",
        ) or []
        result = [
            (code, frappe.db.get_value("Language", code, "language_name") or code)
            for code in codes
        ]
    except Exception:
        result = []
    frappe.cache().set_value(_LANG_CACHE_KEY, result, expires_in_sec=3600)
    return result


def _detect_input_language(text: str) -> str:
    """Return ``"ar"`` when >20 % of characters are Arabic script, else ``"en"``."""
    stripped = text.strip()
    if not stripped:
        return "en"
    arabic_chars = sum(1 for c in stripped if "؀" <= c <= "ۿ")
    return "ar" if arabic_chars / len(stripped) > 0.2 else "en"


def _language_rule(text: str) -> str:
    """
    Build the language-enforcement instruction appended to every LLM prompt.

    * No rows configured → auto-detect from input text.
    * Rows configured    → enforce the matched (or first) allowed language.
    """
    allowed = get_allowed_languages()
    if not allowed:
        return _auto_detect_language_rule(text)
    codes = [c for c, _ in allowed]
    detected = _detect_input_language(text)
    reply_code = detected if detected in codes else codes[0]
    reply_name = next(n for c, n in allowed if c == reply_code)
    return _single_language_rule(reply_name)


def _single_language_rule(name: str) -> str:
    return (
        f"IMPORTANT: Reply ONLY in {name}. Do NOT add any translation, "
        f"bilingual content, or text in any other language.\n"
        f"تعليمات إلزامية: أجب باللغة {name} فقط. ممنوع إضافة ترجمة أو نص بأي لغة أخرى."
    )


def _auto_detect_language_rule(text: str) -> str:
    arabic_chars = sum(1 for c in text if "؀" <= c <= "ۿ")
    if arabic_chars / max(len(text.strip()), 1) > 0.2:
        return (
            "CRITICAL LANGUAGE RULE: You MUST reply in Arabic ONLY. "
            "Do NOT include Chinese characters, English text, or any other language. "
            "Do NOT add translations. Do NOT write bilingual responses. "
            "Your entire response must be in Arabic.\n"
            "قاعدة اللغة: أجب باللغة العربية فقط. ممنوع تمامًا استخدام الصينية أو الإنجليزية "
            "أو أي لغة أخرى. ممنوع إضافة ترجمة. الرد كاملًا يجب أن يكون بالعربية."
        )
    return (
        "IMPORTANT: Reply ONLY in the same language as the user's message. "
        "Do NOT add translations or switch to a different language."
    )


# ===========================================================================
# Role-based widget access
# ===========================================================================

def get_widget_roles() -> list[str]:
    """
    Return the Frappe roles permitted to use the widget.

    Empty list = all logged-in users are allowed (default).
    Cached 1 hour; busted by ``AISettings.on_update()``.
    """
    cached = frappe.cache().get_value(_WIDGET_ROLES_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        roles = frappe.get_all(
            "AI Widget Role",
            filters={"parent": "AI Settings", "parenttype": "AI Settings"},
            pluck="role",
        ) or []
    except Exception:
        roles = []
    frappe.cache().set_value(_WIDGET_ROLES_CACHE_KEY, roles, expires_in_sec=3600)
    return roles


# ===========================================================================
# DocType schema context
# ===========================================================================

def _doctype_schema_context(doctype: str) -> str:
    """
    Return a compact schema summary for *doctype* for injection into the LLM prompt.

    Mandatory fields are listed first, then the remainder up to
    ``_SCHEMA_FIELD_LIMIT``.  Each line includes the field label, type,
    whether it is required, the Link target (for Link fields), and the
    allowed options (for Select fields).

    Result is cached per DocType in Redis for ``_SCHEMA_CACHE_TTL`` seconds.
    """
    cache_key = f"fi_schema:{frappe.scrub(doctype)}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached

    try:
        meta = frappe.get_meta(doctype)
    except Exception:  # noqa: BLE001
        return ""

    visible = [
        f for f in meta.fields
        if f.fieldtype in _SCHEMA_USEFUL_TYPES and not f.hidden
    ]

    # Required fields always shown first; then Link/Select (high value for
    # creation prompts); then the rest — all capped at _SCHEMA_FIELD_LIMIT.
    def _rank(f) -> tuple:
        return (
            0 if f.reqd else (1 if f.fieldtype in (
                "Link", "Select", "Table") else 2),
            f.idx,
        )

    visible.sort(key=_rank)
    visible = visible[:_SCHEMA_FIELD_LIMIT]

    lines: list[str] = []
    for f in visible:
        parts = [f"  - {f.label} ({f.fieldtype})"]
        if f.reqd:
            parts.append("[required]")
        if f.fieldtype == "Link" and f.options:
            parts.append(f"\u2192 {f.options}")
        if f.fieldtype in ("Select", "Radio") and f.options:
            opts = f.options.strip().replace("\n", ", ")
            parts.append(f"[options: {opts}]")
        lines.append(" ".join(parts))

    if not lines:
        frappe.cache().set_value(cache_key, "", expires_in_sec=_SCHEMA_CACHE_TTL)
        return ""

    result = f"Schema for '{doctype}':\n" + "\n".join(lines)
    frappe.cache().set_value(cache_key, result, expires_in_sec=_SCHEMA_CACHE_TTL)
    return result


# ===========================================================================
# Knowledge retrieval (RAG)
# ===========================================================================

def retrieve_knowledge(query: str, limit: int = 3) -> str:
    """
    Score all knowledge entries from active AI Knowledge Packs against *query*
    and return the top *limit* entries as a formatted context block.

    Scoring: count of query words (>3 chars) found anywhere in topic + content.
    Returns ``""`` when nothing useful is found.
    """
    try:
        words = [w for w in query.lower().split() if len(w) > 3]
        if not words:
            return ""

        active_packs = frappe.get_all(
            "AI Knowledge Pack", filters={"is_active": 1}, pluck="name"
        )
        if not active_packs:
            return ""

        entries = frappe.get_all(
            "AI Knowledge Entry",
            filters={"parent": ["in", active_packs],
                     "parenttype": "AI Knowledge Pack"},
            fields=["topic", "content"],
        )
        if not entries:
            return ""

        scored = [
            (sum(1 for w in words if w in f"{e.topic} {e.content}".lower()), e)
            for e in entries
        ]
        top = sorted(
            [(s, e) for s, e in scored if s > 0],
            key=lambda x: x[0],
            reverse=True,
        )[:limit]

        if not top:
            return ""

        sections = "\n\n".join(f"**{e.topic}**\n{e.content}" for _, e in top)
        return f"Relevant knowledge:\n\n{sections}\n\n---"
    except Exception:  # noqa: BLE001
        return ""


# ===========================================================================
# Frappe tool execution
# ===========================================================================

def _to_url_slug(value: str) -> str:
    """Convert a DocType name or record name to a Frappe URL slug (hyphens, lowercase)."""
    return value.lower().replace(" ", "-").replace("_", "-")


def _safe_route(route: str) -> str:
    """
    Return *route* if it starts with ``/app/``, otherwise ``/app``.

    Prevents a manipulated LLM response from producing an open redirect
    to an external URL or a non-SPA route.
    """
    if isinstance(route, str) and route.startswith("/app/"):
        return route
    return "/app"


def execute_tool(tool_name: str, args: dict) -> dict:
    """Convert a model tool call into a widget ``{action, action_data}`` payload."""
    if tool_name == "navigate":
        route = _safe_route(args.get("route", "/app"))
        return {
            "action": "navigate",
            "action_data": {"route": route, "label": args.get("label", "")},
        }

    if tool_name == "open_record":
        doctype = str(args.get("doctype") or "")
        docname = str(args.get("docname") or "")
        if not doctype or not frappe.db.exists("DocType", doctype):
            return {"action": None, "action_data": None}
        return {
            "action": "open_record",
            "action_data": {
                "route": f"/app/{_to_url_slug(doctype)}/{_to_url_slug(docname)}",
                "doctype": doctype,
                "docname": docname,
            },
        }

    if tool_name == "create_record":
        doctype = str(args.get("doctype") or "")
        defaults = args.get("defaults") or {}
        if not doctype or not frappe.db.exists("DocType", doctype):
            return {"action": None, "action_data": None}
        return {
            "action": "create_record",
            "action_data": {
                "route": f"/app/{_to_url_slug(doctype)}/new",
                "doctype": doctype,
                "defaults": defaults,
            },
        }

    if tool_name == "search_records":
        return do_search_records(args.get("doctype", ""), args.get("query", ""))

    return {"action": None, "action_data": None}


def tool_reply_text(tool_name: str, args: dict) -> str:
    """Return a human-readable confirmation message for a tool call."""
    if tool_name == "navigate":
        label = args.get("label") or args.get("route", "that page")
        return frappe._("Navigating to {0}…").format(label)
    if tool_name == "open_record":
        return frappe._("Opening {0} {1}…").format(args.get("doctype", ""), args.get("docname", ""))
    if tool_name == "create_record":
        return frappe._("Creating {0}…").format(args.get("doctype", ""))
    if tool_name == "search_records":
        return frappe._("Searching for '{0}' in {1}…").format(
            args.get("query", ""), args.get("doctype", ""))
    return ""


def do_search_records(doctype: str, query: str) -> dict:
    """Search *doctype* records whose name contains *query* (max 5 results)."""
    base: dict = {"action": "search_results", "action_data": {
        "doctype": doctype, "query": query, "results": []}}
    try:
        if not doctype or not frappe.db.exists("DocType", doctype):
            return base
        if not frappe.has_permission(doctype, ptype="read"):
            return base
        rows = frappe.get_all(
            doctype, filters=[["name", "like", f"%{query}%"]], fields=["name"], limit=5
        )
        base["action_data"]["results"] = [r.name for r in rows]
    except Exception:  # noqa: BLE001
        pass
    return base


# ===========================================================================
# Location fast-path
# ===========================================================================

def handle_location_query(doctype: str, docname: str) -> dict | None:
    """
    Find geo-coordinates for *doctype/docname* from completed AI Processing Logs.

    Checks nested ``geo_coordinates`` dict and flat ``lat``/``lon`` fields.
    Returns ``{"lat", "lon", "map_url"}`` or ``None`` if not found.
    """
    logs = frappe.get_all(
        "AI Processing Log",
        filters={
            "linked_doctype": doctype,
            "linked_docname": docname,
            "processing_status": "Completed",
        },
        fields=["extracted_data"],
        order_by="creation desc",
        limit=10,
    )

    for log in logs:
        raw = log.extracted_data or "{}"
        try:
            data = _json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue

        coords = data.get("geo_coordinates")
        if coords:
            if isinstance(coords, str):
                try:
                    coords = _json.loads(coords)
                except Exception:
                    coords = None
            if coords and isinstance(coords, dict):
                lat = coords.get("latitude") or coords.get("lat")
                lon = coords.get("longitude") or coords.get("lon")
                if lat and lon:
                    return {"lat": str(lat), "lon": str(lon),
                            "map_url": f"https://maps.google.com/?q={lat},{lon}"}

        lat = data.get("latitude") or data.get("lat")
        lon = data.get("longitude") or data.get("lon")
        if lat and lon:
            return {"lat": str(lat), "lon": str(lon),
                    "map_url": f"https://maps.google.com/?q={lat},{lon}"}

    return None


# ===========================================================================
# Intent classification — main entry point
# ===========================================================================

def classify_text_intent(
    text: str,
    doctype: str | None,
    docname: str | None,
    widget_mode: str = "global",
    channel: str | None = None,
    channel_id: str | None = None,
    workflow_key: str | None = None,
) -> dict:
    """Classify *text* and return a structured intent reply.

    When *channel*, *channel_id*, and *workflow_key* are provided the call
    enters **workflow mode**: scope is enforced, the active step drives the
    prompt, and history is read from the persistent AI Agent Session DocType
    rather than the Redis fi_chat key.

    Without those parameters (the default) the function behaves exactly as
    before — Redis history, free-chat mode, desk tools available.

    Returns
    -------
    ``{"reply": str, "action": str | None, "action_data": dict | None}``
    """
    # ------------------------------------------------------------------
    # Workflow mode — scope gate + step-driven prompt
    # ------------------------------------------------------------------
    if channel and channel_id and workflow_key:
        return _classify_workflow_mode(
            text=text,
            channel=channel,
            channel_id=channel_id,
            workflow_key=workflow_key,
        )

    # ------------------------------------------------------------------
    # Legacy free-chat mode (Frappe desk, no workflow)
    # ------------------------------------------------------------------
    text_lower = text.lower()

    # Fast-path: location / map query
    if any(pat.lower() in text_lower for pat in _LOCATION_PATTERNS) and doctype and docname:
        map_data = handle_location_query(doctype, docname)
        if map_data:
            reply = (
                f"📍 Found coordinates for this record: "
                f"{map_data['lat']}, {map_data['lon']}. "
                f"Click the map button to open in Google Maps."
            )
            return {"reply": reply, "action": "map", "action_data": map_data}

    # Build context hint — only include for action/navigation requests to avoid
    # padding the prompt (and inflating time-to-first-token) on conversational messages.
    needs_action = _needs_tools(text)
    if needs_action and widget_mode == "proactive" and doctype and docname:
        context_hint = (
            f"The user is currently editing the '{doctype}' record named '{docname}'. "
            f"Help them with document extraction, field lookups, or record-related questions."
        )
    elif needs_action and widget_mode == "global":
        context_hint = (
            "The user is on a general overview page (not a specific record). "
            "Help them navigate the system, search for records, or answer ERP questions. "
            "If they want to go to a specific page, tell them the Frappe route "
            "(e.g. /app/customer or /app/facility)."
        )
    elif needs_action and doctype and docname:
        context_hint = (
            f"The user is currently viewing a '{doctype}' record named '{docname}'."
        )
    else:
        context_hint = ""

    knowledge_context = retrieve_knowledge(text)
    schema_context = _doctype_schema_context(doctype) if doctype else ""
    lang_rule = _language_rule(text)

    # Language rule goes FIRST so the model's language frame is set before
    # it reads the English context hints.  User message is XML-delimited to
    # prevent prompt injection.
    prompt = (
        f"{lang_rule}\n\n"
        + (f"{knowledge_context}\n\n" if knowledge_context else "")
        + (f"{schema_context}\n\n" if schema_context else "")
        + f"{context_hint}\n\n"
        + f"<user_message>\n{text}\n</user_message>"
    )

    history = get_chat_history()
    tools = FRAPPE_TOOLS if _needs_tools(text) else []

    from frappe_intelligence.models.llm_factory import get_adapter  # noqa: PLC0415
    adapter = get_adapter()
    value, error = adapter.chat(prompt, history=history, tools=tools)

    if error:
        return {
            "reply": f"Could not reach the AI model ({error}). Please try again.",
            "action": None,
            "action_data": None,
        }

    # Tool call from the model
    if isinstance(value, dict) and "__tool__" in value:
        tool_name = value["__tool__"]
        args = value.get("args", {})
        result = execute_tool(tool_name, args)
        append_to_chat_history("user", prompt)
        append_to_chat_history("assistant", f"[action: {tool_name}]")
        return {"reply": tool_reply_text(tool_name, args), **result}

    reply = str(value) if value else frappe._(
        "Sorry, I could not generate a reply. Please try rephrasing."
    )
    if value:
        append_to_chat_history("user", prompt)
        append_to_chat_history("assistant", reply)

    return {"reply": reply, "action": None, "action_data": None}


# ===========================================================================
# Workflow mode — internal implementation
# ===========================================================================

def _classify_workflow_mode(
    text: str,
    channel: str,
    channel_id: str,
    workflow_key: str,
) -> dict:
    """Handle classify_text_intent when a workflow session is active.

    Pipeline:
      1. Get / create AI Agent Session
      2. Scope gate — return out_of_scope_reply without touching LLM if out of scope
      3. Build step-specific prompt from current step + collected data
      4. Call LLM with session turn history
      5. Persist turns to session
    """
    from frappe_intelligence.engine import scope as _scope    # noqa: PLC0415
    from frappe_intelligence.engine import workflow as _wf    # noqa: PLC0415

    session = _wf.get_or_create_session(channel, channel_id, workflow_key)
    workflow_doc = _wf.get_workflow(session)

    # --- Scope gate ---
    if workflow_doc:
        in_scope, redirect = _scope.check_scope(text, workflow_doc)
        if not in_scope:
            _wf.append_turn(session, "user", text)
            _wf.append_turn(session, "assistant", redirect)
            return {"reply": redirect, "action": None, "action_data": None}

    # --- Build prompt from current step ---
    step = _wf.get_current_step(session)
    if session.status == "abandoned":
        reply = (
            "This session was reset because the workflow was updated. "
            "Please start a new conversation."
        )
        _wf.append_turn(session, "user", text)
        _wf.append_turn(session, "assistant", reply)
        return {"reply": reply, "action": None, "action_data": None}
    lang_rule = _language_rule(text)
    knowledge_context = retrieve_knowledge(text)

    if step:
        collected = _wf.get_collected_for_step(session, step.step_key)
        step_prompt = _wf.build_step_prompt(step, collected, workflow_doc)
        prompt = (
            f"{lang_rule}\n\n"
            + (f"{knowledge_context}\n\n" if knowledge_context else "")
            + f"{step_prompt}\n\n"
            + f"<user_message>\n{text}\n</user_message>"
        )
    else:
        # No active step — workflow complete or free-form within scope.
        # If the workflow defines a completion_message, return it immediately
        # without touching the LLM (no tokens consumed, deterministic reply).
        if workflow_doc and getattr(workflow_doc, "completion_message", None):
            completion = workflow_doc.completion_message
            _wf.append_turn(session, "user", text)
            _wf.append_turn(session, "assistant", completion)
            return {"reply": completion, "action": None, "action_data": None}

        context = (
            "The user's workflow is complete. "
            "Answer any follow-up questions within the scope of this service."
        )
        if workflow_doc and workflow_doc.scope_description:
            context = workflow_doc.scope_description
        prompt = (
            f"{lang_rule}\n\n"
            + (f"{knowledge_context}\n\n" if knowledge_context else "")
            + f"{context}\n\n"
            + f"<user_message>\n{text}\n</user_message>"
        )

    # --- LLM call with session history ---
    history = _wf.get_turn_history(session)

    from frappe_intelligence.models.llm_factory import get_adapter  # noqa: PLC0415
    adapter = get_adapter()
    # Workflow mode never exposes desk navigation tools — they're meaningless
    # on portal / WhatsApp channels where frappe.set_route() doesn't exist.
    value, error = adapter.chat(prompt, history=history, tools=[])

    if error:
        reply = f"Could not reach the AI model ({error}). Please try again."
        _wf.append_turn(session, "user", text)
        _wf.append_turn(session, "assistant", reply)
        return {"reply": reply, "action": None, "action_data": None}

    reply = str(value) if value else frappe._(
        "Sorry, I could not generate a reply. Please try rephrasing."
    )

    _wf.append_turn(session, "user", text)
    _wf.append_turn(session, "assistant", reply)

    return {"reply": reply, "action": None, "action_data": None, "session": session.name}
