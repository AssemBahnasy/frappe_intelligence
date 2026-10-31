# Server side

```
browser: api.writer.write_field(doctype, fieldname, instruction, current, context, docname)
  → assistant access; Write with AI turned on
  → the field: a long text type, not read-only, at a permission level the user can write;
    create permission on the DocType (new form) or write permission on the record
  → context: the form's other values, only fields the user can read, by label, 40 at most, 300 characters each
  → writer.text.start → background job (queue long, 10 minutes) → {"job": id}

job: writer.text.run
  → the model writes the text (AI Settings provider, system prompt and response language)
  → result kept 10 minutes under the user's own key → realtime fi_field_writer {job, text | error}

browser: waits for the event; every 10 seconds asks get_written(job) in case it was missed; gives up after 10 minutes
```

## What the model reads

| Part | Content |
|---|---|
| System | AI Settings system prompt; return only the field's text; never invent names, numbers or dates; plain text, or short paragraphs and lists for Text Editor and Markdown Editor |
| User | The DocType and field label; the other values on the form; the field's current text; what the user asked; the language rule for their request |

Fences or quotes around the reply are removed.

## Security

| Risk | Guard |
|---|---|
| Writing a field the user may not edit | Field type, `read_only` and permission level checked on the server; DocType create or record write permission |
| Reading values through the prompt | Only fields at a permission level the user can read; Password, Attach, Signature, Code, JSON and Geolocation fields are left out |
| Another user's result | Results are stored under the user's own key |
| Saving without the user | Nothing is saved; the text goes into the form and the user saves it |
| Cost | Frappe rate limit on `write_field` (20 a minute per user); description up to 2000 characters, current text up to 10,000 |
