# Portal (`api.portal`)

| Endpoint | Auth | Notes |
|----------|------|-------|
| `portal_chat` | Portal User table check | Workflow mode only; the workflow must be Active with Allow Portal |
| `portal_upload_document` | Portal User table check | Enqueues async job |
| `portal_get_session_state` | Portal User table check | Returns current step + collected data |

`portal_chat` and `portal_upload_document` are rate limited ([README.md](README.md#access-and-rate-limits)). Portal conversations go through `workflows.sessions.reply` ([../workflows/turn.md](../workflows/turn.md)).
