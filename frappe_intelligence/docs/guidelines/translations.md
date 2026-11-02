# Translations

## Strings

Every user-facing string goes through `_()` (or `_lt()` at import time) in Python and `__()` in JavaScript and Vue; DocType labels and descriptions are picked up from the JSON. Arabic ships in `locale/ar.po` (gettext, like Frappe, ERPNext and HRMS); `locale/main.pot` lists every string.

After adding or changing strings:

```bash
bench generate-pot-file --app frappe_intelligence
bench update-po-files --app frappe_intelligence --locale ar
# translate the new empty msgstr entries in locale/ar.po
bench compile-po-to-mo --app frappe_intelligence --locale ar
```

`bench build` also compiles them. Text sent to a model is not translated: it stays in English.

## Values that vary by language

A value that differs by language is never a field per language (`address_ar`, `address_en`). It is a child table with a **Language** link (Frappe's Language, named by code: `ar`, `en`, `fr`) and the text, both required, with the language unique per record. A new language is then a row, not a schema change.

## The reply language

What language the assistant replies in, and how replies written without AI follow it: [../panel/language.md](../panel/language.md).
