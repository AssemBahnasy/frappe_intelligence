# Settings (`api.settings`)

## Connection

### `test_connection`

Checks the active AI provider (AI Settings → Test Connection). System Manager only.

```json
{"ok": true}
// or
{"ok": false, "error": "Cannot connect to Ollama at http://localhost:11434"}
```

## WhatsApp

Whether the `frappe_whatsapp` app is installed, and whether AI Settings → Enable AI on WhatsApp is on.

### `is_whatsapp_installed`

```json
true
```

### `is_whatsapp_enabled`

```json
true
```
