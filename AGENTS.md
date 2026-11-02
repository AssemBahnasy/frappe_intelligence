# Agent instructions

Before changing anything in this repository, read [frappe_intelligence/docs/README.md](frappe_intelligence/docs/README.md), then [frappe_intelligence/docs/guidelines/](frappe_intelligence/docs/guidelines/README.md), then the docs folder of the feature you are working on.

The rules that matter most:

- **Frappe's way.** Follow the layout and style of Frappe, ERPNext, HRMS and CRM; check every mechanism in Frappe's source before relying on it.
- **Separation of concerns and DRY.** Endpoints in `api/` only check access and inputs; logic lives in the feature packages; only `providers/` talks to an AI service.
- **UI needs an approved mockup** before any implementation code.
- **One step at a time.** Build, verify (tests, migrate, build, browser), document, then stop for review.
- **Docs ship with the change**, in the feature's folder, one short file per concern.
- **The tutorial ships with the change**: a new or changed feature adds or updates its topic ([frappe_intelligence/docs/tutorial/content.md](frappe_intelligence/docs/tutorial/content.md)).
- **Strings are translated** (`_()`, `__()`, `locale/ar.po`); text sent to a model stays in English.
- **Tests run over fakes** and never import the optional OCR or voice packages.
