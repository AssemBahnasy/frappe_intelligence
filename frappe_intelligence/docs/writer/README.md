# Write with AI

A sparkles button beside long text fields in every form. The user says what the field should say, the AI writes it in place, and **Undo** puts the old text back. Nothing is saved: the user saves the form (approved board 3d).

| Concern | Doc |
|---|---|
| What the user sees: button, popover, toast, Undo | [behaviour.md](behaviour.md) |
| The endpoint, the background job, what the model reads, permissions | [server.md](server.md) |

Turned on or off in **AI Settings → Assistant → Write with AI in Forms** (on by default; the patch `v1_0.enable_field_writer` turns it on for sites that had AI Settings before). It follows **Allowed Roles** like the rest of the assistant.

## Code

| Piece | Responsibility |
|---|---|
| `public/js/fi_field_writer.bundle.js` | Buttons on every form (`frappe.ui.form.on("*", "refresh")`), popover, waiting for the text, Undo |
| `public/css/fi_field_writer.bundle.css` | Button, popover, the ring around a field just written |
| `api/writer.py` | `write_field`: which field may be written, which form values the model reads |
| `writer/text.py` | The prompt and the model call, run as a background job (`utils/background.py`) |
| `boot.py` | `fi_assistant.field_writer`: the field types that get the button, empty when turned off |
