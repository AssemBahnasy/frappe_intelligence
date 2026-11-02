# Write with AI, voice and background jobs

## Write with AI (`api.writer`)

### `write_field`

POST only. Writes one long text field in the background and returns `{"job": id}`; the text is the job's value (see [Background jobs](#background-jobs-apijobs)). See [writer/server.md](../writer/server.md).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `doctype` | str | ✓ | |
| `fieldname` | str | ✓ | Small Text, Text, Long Text, Text Editor or Markdown Editor, editable by the user |
| `instruction` | str | ✓ | What the field should say; up to 2000 characters |
| `current` | str | ✗ | The field's current text |
| `context` | object | ✗ | The form's other values by field name; only readable fields are used |
| `docname` | str | ✗ | Omit on a new form |

## Voice input (`api.voice`)

### `transcribe`

POST only. `file_url`: a recording the user just uploaded as a private File. Turns it into text in the background (Whisper, on this server) and returns `{"job": id}`; the text is the job's value. The recording is deleted afterwards. Refused when the voice package is not installed. See [panel/voice.md](../panel/voice.md).

## Background jobs (`api.jobs`)

Write with AI and voice input run as short background jobs (`utils/background.py`). The result arrives on the `fi_job` realtime event as `{job, value}` or `{job, error}`.

### `job_result`

`job`: a job the user started. Returns `{value}`, `{error}` or `{pending: true}`; for a browser that missed the event.
