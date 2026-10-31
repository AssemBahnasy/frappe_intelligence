# Workflows

An AI Workflow is a named, ordered sequence of steps that guides a user through a business process. The engine enforces scope (no off-topic messages), collects required data step-by-step, and advances automatically when each step is complete. How a turn runs and how the panel shows it: [workflows/README.md](workflows/README.md).

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
| `is_active` | Inactive workflows cannot be started or continued |
| `allow_desk` / `allow_portal` / `allow_whatsapp` | Enable per channel |
| `scope_description` | Plain-language mandate — injected into LLM system prompt; used for cosine similarity scope check |
| `out_of_scope_reply` | Reply returned when the user's message is out of scope (no LLM call) |
| `excluded_keywords` | One term per line — bypasses the keyword gate for domain-specific terms |
| `confidence_threshold` | Per-workflow override (0 = use global AI Settings value) |
| `completion_message` | Shown when all steps complete, without AI; empty means a list of the answers |

## Steps

Each **AI Workflow Step** child row defines one collection step:

| Field | Purpose |
|-------|---------|
| `step_order` | Execution order (integer) |
| `step_key` | Short code identifier (unique within workflow) |
| `prompt_to_user` | The step's question, asked without AI when the step starts |
| `target_doctype` | The record its answers fill; on the desk a filled new form opens when its steps are done |
| `required_fields` | `{field key: label}` the user must supply; keys are the Target DocType's field names |
| `completion_check` | Optional dotted path to `check(values, collected)` in an installed app ([workflows/steps.md](workflows/steps.md#completion-check)) |
| `next_step_key` | Explicit next step; auto-advances sequentially if empty |
| `whatsapp_flow` | Link to WhatsApp Flow (interactive form sent over WhatsApp) |

Step keys must be unique within the workflow. Duplicate keys are rejected at save.

## Scope Enforcement

Off-topic messages get the workflow's `out_of_scope_reply` and the current question, without a model call: a phrase check first, then, for a message that answered nothing, word overlap with `scope_description`. `excluded_keywords` let a message through. Details: [workflows/turn.md](workflows/turn.md#the-topic-gate).

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
    "frappe_intelligence.api.documents.register_post_processor",
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
| Paused | The user pressed **Exit** in the panel; answering again continues |

On the desk, a workflow is a conversation of its own, reopened from History. Portal and WhatsApp conversations are keyed by `(channel, channel_id, workflow)`: the same user picks up their Active or Paused one.

## WhatsApp Flows

For WhatsApp channel steps, set `whatsapp_flow` to a WhatsApp Flow record. The engine sends the interactive flow form to the user and processes the submitted `flow_response` JSON. Requires `allow_whatsapp=1` on the workflow and the WhatsApp tab configured in AI Settings.
