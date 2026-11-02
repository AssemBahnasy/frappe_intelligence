# Guidelines

The rules every change follows. They come from Frappe's own apps (Frappe, ERPNext, HRMS, CRM): when a rule here is unclear, do what those apps do.

| Concern | Doc |
|---|---|
| Code layout, separation of concerns, DRY, Python and form-script style | [code.md](code.md) |
| UI: mockups first, Vue in the desk, icons, right to left | [ui.md](ui.md) |
| Translations and values that vary by language | [translations.md](translations.md) |
| Tests, linting and CI | [testing.md](testing.md) |
| Writing and placing docs | [docs.md](docs.md) |

## How work is done

- **One step at a time.** Build one step, verify it (migrate, build, tests, the browser where it shows), document it, then stop for review before the next. A list of fixes approved as a whole is done in one go.
- **Verify in Frappe's source.** Check every mechanism used (a hook, a desk API, a DocType behaviour) in Frappe's own code before relying on it; cite where it comes from in the docs.
- **Docs ship with the change.** A change is not done until its feature folder says what it does now.
