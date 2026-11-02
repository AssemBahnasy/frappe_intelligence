# Docs

## Where things go

| Content | Place |
|---|---|
| A feature | Its own folder (`agent/`, `panel/`, `workflows/` ...) |
| A rule for every change | `guidelines/` |
| How the pieces fit | `overview/` |
| Installing, settings, integrating | `setup/` |
| Endpoints | `api/`, one file per `api/` module |

## How they are written

- File and folder names are lowercase with hyphens (`live-replies.md`).
- Each folder has a `README.md` that is only an index: one line per file, plus a short code map.
- Each file covers one concern and fits on about one screen. It links to other files instead of repeating them.
- Facts are checked against the code and Frappe's source; cite the file or function that does it.
- Plain words and short sentences; tables for fields, settings and options.
- Docs are written with the change, and say what the code does now, not its history (history goes in [../overview/history.md](../overview/history.md)).

## Links

Links are relative, so they work on GitHub and in an editor. After moving or renaming a file, check that no link points to it.
