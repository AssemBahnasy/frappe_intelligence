# Testing

## Tests

Tests run over fakes: no API keys, model or network needed. Run them all on a site with the app installed:

```bash
bench --site <site> run-tests --app frappe_intelligence
bench --site <site> run-tests --app frappe_intelligence --module frappe_intelligence.tests.test_agent
```

| Module | Covers |
|---|---|
| `tests/test_agent.py` | Agent loop, Stop, tools, prompts, conversation history, reply language |
| `tests/test_runs.py` | Background runs and realtime events |
| `tests/test_providers.py` | Every provider over a fake SDK |
| `tests/test_extractor.py` | AI field extraction |
| `tests/test_documents.py` | Templates, document review, transcript |
| `tests/test_workflows.py` | Steps, topic gate, answers, turns |
| `tests/test_writer.py` | Write with AI |
| `tests/test_background.py` | Short background jobs, voice input, optional packages, rate limit |
| `tests/test_tutorial.py` | Tutorial progress, the demo video recorder, its sample data |

A change comes with tests for what it changes. A test checks behaviour, not the implementation.

## Optional packages

The OCR (`easyocr`) and voice (`faster-whisper`) packages are optional extras, and CI installs the app without them. A test that touches them never imports them: it puts a stand-in module in `sys.modules` (`patch.dict(sys.modules, {"faster_whisper": ...})`).

## Linting

Ruff checks and formats Python (`pyproject.toml`). Check only the files you changed:

```bash
ruff check <files>
ruff format <files>
```

## CI

| Workflow | Runs |
|---|---|
| `.github/workflows/ci.yml` | Installs the app on a fresh site and runs the tests (Python 3.14, MariaDB 11.8) |
| `.github/workflows/linter.yml` | pre-commit (ruff, JSON/YAML/TOML checks), Frappe's Semgrep rules, pip-audit |

## Live checks

A change to how the assistant talks to a model is also tried against a real provider before it is called done: a few turns in English and Arabic, with the records it created removed afterwards.
