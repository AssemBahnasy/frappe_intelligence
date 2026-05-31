# Workflows

An AI Workflow is a named, ordered sequence of steps that guides a user through a business process. The engine enforces scope (no off-topic messages), collects required data step-by-step, and advances automatically when each step is complete.

## Workflow Builder

**Frappe desk → Intelligence → AI Workflow Builder** — visual no-code editor (System Manager only).

The builder saves to three DocTypes atomically:
- **AI Workflow** — header, scope, configuration
- **AI Workflow Step** — ordered steps
- **AI Document Requirement** — documents required per step

## AI Workflow Fields

| Field | Purpose |
|-------|---------|
| `workflow_key` | Slug identifier used in code (unique, e.g. `service_request`) |
| `title` | Human-readable name |
| `is_active` | Inactive workflows are not shown in the widget selector |
| `allow_desk` / `allow_portal` / `allow_whatsapp` | Enable per channel |
| `scope_description` | Plain-language mandate — injected into LLM system prompt; used for cosine similarity scope check |
| `out_of_scope_reply` | Reply returned when the user's message is out of scope (no LLM call) |
| `excluded_keywords` | One term per line — bypasses the keyword gate for domain-specific terms |
| `confidence_threshold` | Per-workflow override (0 = use global AI Settings value) |
| `completion_message` | Shown when all steps complete (no LLM call if set) |

## Steps

Each **AI Workflow Step** child row defines one collection step:

| Field | Purpose |
|-------|---------|
| `step_order` | Execution order (integer) |
| `step_key` | Short code identifier (unique within workflow) |
| `prompt_to_user` | Message sent to the user at this step |
| `target_doctype` | Document type to create/link when step completes |
| `required_fields` | JSON array of field keys the user must supply |
| `completion_check` | Optional Python expression evaluated to decide if step is done |
| `next_step_key` | Explicit next step; auto-advances sequentially if empty |
| `whatsapp_flow` | Link to WhatsApp Flow (interactive form sent over WhatsApp) |

Step keys must be unique within the workflow. Duplicate keys are rejected at save.

## Scope Enforcement

Three-layer gate runs before every LLM call in Agent mode:

1. **Excluded keywords** — if any term in `excluded_keywords` appears in the user's message, skip the keyword gate
2. **Keyword gate** — regex patterns block obviously off-topic messages (jokes, weather, arithmetic)
3. **Cosine similarity** — TF-IDF vector comparison of user text vs `scope_description`; below threshold → return `out_of_scope_reply` immediately

Zero LLM tokens spent on rejected messages.

## Knowledge Packs

RAG context injected automatically into each step's LLM prompt.

**AI Knowledge Pack** contains free-text snippets (AI Knowledge Entry child rows):

| Field | Notes |
|-------|-------|
| `pack_name` | Display name |
| `is_active` | Inactive packs are not retrieved |
| `json_file` | Upload a JSON bundle to bulk-import entries |
| `knowledge_entries` | Child table — topic + content |

### Retrieval Algorithm

1. Extract all words > 3 characters from the user's message
2. Score each active Knowledge Entry by keyword overlap
3. Inject top-3 matches as context block before the LLM prompt

No vector DB or embeddings required.

### Assigning Packs to a Workflow

Use the **Knowledge Packs** section in the Workflow Builder, or the `AI Workflow Knowledge Pack` child table directly. Only packs assigned to the workflow are retrieved during that workflow's sessions.

### Seeding from Python

```python
frappe.get_doc({
    "doctype": "AI Knowledge Pack",
    "pack_name": "My App Knowledge",
    "is_active": 1,
    "knowledge_entries": [
        {"topic": "Approval Policy",
         "content": "Purchase orders above 10,000 SAR require manager approval."},
    ],
}).insert(ignore_permissions=True)
```

## Post-Processors

A post-processor is a Python callable enqueued after a successful extraction to auto-fill fields on a linked Frappe record.

### Write a Handler

```python
# your_app/handlers.py
def fill_purchase_invoice(extraction_result, doctype, docname, **kwargs):
    data = extraction_result.get("extracted_data", {})
    if not docname:
        return
    doc = frappe.get_doc(doctype, docname)
    doc.bill_no   = data.get("bill_no", doc.bill_no)
    doc.bill_date = data.get("bill_date", doc.bill_date)
    doc.save(ignore_permissions=True)
```

The `**kwargs` signature is required — the engine passes extra context keys that may change over time.

### Register via API

```python
frappe.call(
    "frappe_intelligence.api.register_post_processor",
    document_type_key="supplier_invoice",
    callback_method="your_app.handlers.fill_purchase_invoice",
    description="Auto-fill Purchase Invoice fields",
)
```

Or via **AI Post Processor → New** in the desk.

### Assign to Workflow Steps

In the Workflow Builder **Post-Processors** section, map `step_key` → processor. Only processors assigned to the current step fire when that step completes.

### Timing

| Scenario | When it fires |
|----------|--------------|
| `confidence_score >= threshold` | Immediately after background job completes |
| `confidence_score < threshold` | After user clicks **Accept** in the review panel |
| User clicks **Discard** | Never fires |

### Security

The `callback_method` must be in a top-level package that matches an installed Frappe app name. Paths outside installed apps are blocked at execution time.

## Session Lifecycle

| Status | Meaning |
|--------|---------|
| Active | In progress |
| Completed | All steps done |
| Abandoned | Idle > 7 days (set by daily scheduler task) |
| Paused | Manually paused |

Sessions are keyed by `(channel, channel_id, workflow)`. The same user resuming a workflow in the same channel picks up the existing session.

## WhatsApp Flows

For WhatsApp channel steps, set `whatsapp_flow` to a WhatsApp Flow record. The engine sends the interactive flow form to the user and processes the submitted `flow_response` JSON. Requires `allow_whatsapp=1` on the workflow and the WhatsApp tab configured in AI Settings.
