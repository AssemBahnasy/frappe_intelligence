# DocTypes

All in the **Intelligence** module.

```
AI Settings (Single)                        → ../setup/settings.md
  ├── AI Response Language   (child: languages the assistant replies in)
  └── AI Excluded DocType    (child: DocTypes Agent mode never changes)

AI Conversation              (desk chats and workflow sessions, every channel)   → ../agent/conversations.md
  └── AI Conversation Message (child: user, assistant, tool and system rows)

AI Workflow                                                                      → ../workflows/building.md
  ├── AI Workflow Step            (child: ordered steps)
  └── AI Workflow Knowledge Pack  (child: packs the workflow searches)

AI Knowledge Pack                                                                → ../workflows/knowledge-packs.md
  └── AI Knowledge Entry     (child: topic and content)

AI Document Template                                                             → ../documents/templates.md
  └── AI Extraction Rule     (child: field key, regex, AI hint)

AI Processing Log            (every document reading)                             → ../documents/training.md
AI Training Pair             (a reading the user corrected)                      → ../documents/training.md
AI Document Requirement      (target DocType → required document type)           → ../documents/pipeline.md
AI Post Processor            (callback registry)                                  → ../workflows/post-processors.md
```

The **AI Session Analytics** report and the **AI Workflow Builder** page live in the same module.
