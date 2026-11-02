# Post-processors

A post-processor is a Python function in an installed app that runs after a document is read through the pipeline ([../documents/pipeline.md](../documents/pipeline.md)), for example to fill a record from the values.

## The function

```python
# your_app/handlers.py
def fill_purchase_invoice(extraction_result, doctype, docname, **kwargs):
	data = extraction_result.get("extracted_data", {})
	if not docname:
		return
	doc = frappe.get_doc(doctype, docname)
	doc.bill_no = data.get("bill_no", doc.bill_no)
	doc.save()
```

Keep `**kwargs`: more keys may be passed later.

## Registering it

An **AI Post Processor** record (document type key, callback method, description, active), made in the desk or with `api.documents.register_post_processor` (System Manager).

## When it runs

Every active post-processor for the document's type is enqueued on the `default` queue (`documents/pipeline.fire_post_processors`):

| Reading | Runs |
|---|---|
| Confidence at or above the threshold | When the background reading finishes |
| Below the threshold | When the user confirms it (`confirm_extraction`) |
| Discarded | Never |

The document type alone decides: post-processors are not tied to workflows or their steps.

## Safety

The callback's top-level package must be an installed Frappe app (`utils/callables`); anything else is skipped and logged as an unsafe callback.
