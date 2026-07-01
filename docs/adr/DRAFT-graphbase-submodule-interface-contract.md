# ADR-XXXX — Formalize the graphbase submodule interface; keep it a submodule

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

`graphbase` is a git submodule with its own FastAPI application. Two callers
in the parent package import from it:

- `codecarto/main.py` — mounts the `graphdb` APIRouter at `/db`
- `codecarto/services/cache_service.py` — borrows the shared MongoClient
  via `get_db()` to avoid opening a second connection

Both used `from graphbase.src.main import ...` — a path that reaches into
the submodule's internal module layout. Any future restructuring of
`graphbase/src/` (e.g. splitting `main.py` into multiple files) would
silently break these callers because Python resolves the import at runtime;
there is no static import boundary.

Additionally, the conditional mount block in `main.py` had a `try/except`
that swallowed all errors silently. This made a misconfigured `MONGODB_URI`
(or a shell that doesn't inherit the env var — git-bash does not pick up
Windows user-scope env vars set via PowerShell or the registry) completely
invisible at startup. The 404 on `GET /db/` was the only signal, which only
appeared when a frontend request was already in flight.

## Decision

- Expose `graphdb` and `get_db` from `graphbase/src/__init__.py` as the
  package's documented public surface. Callers import `from graphbase import
  graphdb, get_db` — a single-module path that remains stable even if
  `graphbase/src/main.py` is later split.
- `graphbase` stays a submodule. Its standalone deployability (it ships its
  own FastAPI app and `docker-compose.yml`) is a feature, not incidental.
  Absorbing it into `codecarto` would tie releases together and remove the
  ability to run graphbase as an independent service.
- Replace the silent `try/except` in `main.py` with explicit `logging.info`
  on success, `logging.error` on import failure, and a `logging.info` when
  `MONGODB_URI` is absent that names the git-bash env-var inheritance gap
  specifically — because this was the actual failure mode encountered, and
  the log message is the fastest path to diagnosis for the next occurrence.

## Consequences

- A future restructuring of `graphbase/src/` only requires updating
  `graphbase/src/__init__.py`, not every caller in the parent package.
- The startup log makes environment misconfiguration immediately visible:
  developers see either "mounted at /db" or "set MONGODB_URI …" on every
  server start, with a note about git-bash specifically.
- The `graphbase/src/__init__.py` is now a versioned contract surface. Any
  removal of `graphdb` or `get_db` from it is a breaking change to
  `codecarto` and must be coordinated as a submodule update, not a silent
  internal refactor.

## Alternatives considered

1. **Absorb `graphbase` into `codecarto` as an inline module** — rejected:
   the submodule's standalone deployability is intentional and must be
   preserved per project requirements.
2. **Leave imports as `from graphbase.src.main import ...`** — rejected:
   the internal-path import is fragile; the public-surface pattern costs
   nothing and removes a class of silent breakage.

## Revision triggers

- The `graphbase` submodule gains additional exportable symbols that
  `codecarto` needs — extend `__init__.py` rather than reaching back into
  `graphbase.src.*`.
- A second project depends on `graphbase` — document the contract in the
  submodule's own README at that point.

## Amendments

*None.*
