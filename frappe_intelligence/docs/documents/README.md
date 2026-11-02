# Documents

Files the assistant reads: PDFs, photos and text files. A file that matches an **AI Document Template** comes back as fields the user checks first; the values they confirm are what gets used.

| Concern | Doc |
|---|---|
| Attaching a file in the panel and reviewing what was read (board 3a) | [review.md](review.md) |
| Templates, extraction rules, extraction mode, the files that can be read, seeding | [templates.md](templates.md) |
| The pipeline for the portal, WhatsApp and other apps; document requirements | [pipeline.md](pipeline.md) |
| Processing logs and training pairs | [training.md](training.md) |

## Code

| Piece | Responsibility |
|---|---|
| `documents/reader.py` | Text from a PDF (embedded text or OCR), an image (OCR) or a text file |
| `documents/templates.py` | Which template a text matches; field values by its Model Preference |
| `documents/heuristic.py`, `extractor.py` | Regex rules; AI-provider extraction |
| `documents/review.py` | The panel's reading: review card, confirmed values, training pairs, log links |
| `agent/tools/documents.py` | The `read_document` tool |
| `documents/pipeline.py` | The portal, WhatsApp and integrations pipeline (`AIEngine`), using `templates.py` |
| `documents/voice.py`, `transcriber.py` | Voice input: a recording from the panel to text ([../panel/voice.md](../panel/voice.md)) |
