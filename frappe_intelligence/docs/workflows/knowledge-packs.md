# Knowledge packs

An **AI Knowledge Pack** holds the company's own facts and policies as entries (**AI Knowledge Entry**: topic and content). No embeddings or vector store: entries are found by shared words (`agent/tools/knowledge.py`).

| Field | Purpose |
|---|---|
| Pack Name | Display name |
| Is Active | Inactive packs are never searched |
| JSON File | A JSON bundle whose entries are imported on save |
| Knowledge Entries | Topic and content |

## Search

The words of at least 4 letters in the question are counted in each entry's topic and content; the 3 entries with the most matches are used.

| Where | Packs searched | How |
|---|---|---|
| Ask and Agent modes | Every active pack | The `search_knowledge` tool, which the model calls for how-to and policy questions |
| Guided workflows | Only the workflow's own packs | Matching entries are added to the model's instructions each turn |

## Seeding

```python
frappe.get_doc({
	"doctype": "AI Knowledge Pack",
	"pack_name": "My App Knowledge",
	"is_active": 1,
	"knowledge_entries": [
		{"topic": "Approval Policy", "content": "Purchase orders above 10,000 SAR need a manager's approval."},
	],
}).insert(ignore_permissions=True)
```
