# The document pipeline

How the portal, WhatsApp and other apps have a document read. The desk panel does not use it: it reads attached files through the agent ([review.md](review.md)). Both share `documents/templates.py`.

## Flow

```
api.documents.process_document(file_url, target_doctype=None)
  → file access checked → AI Processing Log (Pending) → background job on the long queue
  ← {"status": "queued", "log_name": …}                     immediate

documents/pipeline.process_document_background
  → text read → template matched (by key, or by keywords) → fields extracted
  → log Completed (values, confidence) or Failed
  → confidence ≥ threshold: post-processors fire
  → realtime event ai_processing_complete to the user who asked
```

A browser that missed the event asks `get_log_status`. A reading below the threshold waits for `confirm_extraction`, which then fires the post-processors; a correction is saved with `submit_correction` ([training.md](training.md)). Endpoints: [../api/documents.md](../api/documents.md).

## Post-processors

Python callbacks that fill a record from the values read: [../workflows/post-processors.md](../workflows/post-processors.md).

## Document requirements

An **AI Document Requirement** says which document types a DocType's records need (`target_doctype`, `document_type_key`, `label`). Requirements belong to a DocType, not to a workflow or its steps. `api.documents.get_required_documents(doctype, docname)` returns which are present and which are missing, judged by the processing logs linked to the record. Integrating apps seed them ([../setup/integration.md](../setup/integration.md#seeding-requirements)).

## Code

| Piece | Job |
|---|---|
| `documents/pipeline.py` | `AIEngine` (read, match, extract, log), the background job, firing post-processors, linking a log to a record |
| `api/documents.py` | The endpoints |
| `channels/whatsapp.py` | WhatsApp images and documents go through the same engine |
