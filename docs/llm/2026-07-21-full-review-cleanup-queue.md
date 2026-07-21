# 2026-07-21 full-review cleanup queue

Survey of the codebase (2026-07-21) triggered by two same-session
dependency-triage near-misses (see `docs/qm/perspectives/
2026-07-21-verify-before-fixing.md` and the companion
`docs/qm/adr/DRAFT-verify-actual-consumption-before-editing.md` on this
project's `project/codecartographer` branch): a dead `requirements.txt`
misdiagnosed as load-bearing, then several merged Dependabot PRs that
only touched that dead file. Following up turned into a full-repo
review — three parallel research passes (backend, frontend, docs) plus
direct checks — for dead code, doc drift, dependency-declaration
mismatches, and repo hygiene.

Same format as `docs/llm/archive/legacy/parser_consolidation_and_scope_
drift.md`: numbered findings, file:line references, a planned action,
`[DONE]` markers added as each item ships on branch
`cleanup/2026-07-21-full-review`.

One flagged item — the `/lexicon` router — turned out **not** to be dead
code: it's documented, deliberate infrastructure
(`docs/llm/roadmap/lexicon.md`). It's excluded from this queue and
instead seeds `docs/llm/roadmap/topology-functionality-abstraction-
maps.md`.

---

## 1. qm governance migration [DONE 2026-07-21]

**Status: done.**

Adopt the branch-per-project ADR model from `quaternionmedia/qm` commit
`d1b8afc`: this project's `adr/` directory moves from a copy inside
this repo (`docs/adr/`) to a dedicated branch of the `qm` repo
(`project/codecartographer`), checked out through the `docs/qm`
submodule.

- `.gitmodules`: `docs/qm` submodule tracks `branch =
  project/codecartographer` instead of a floating `main` pin.
- `docs/adr/` (this repo's own copy, 10 `DRAFT-*.md` files) deleted —
  same content now lives unchanged at `docs/qm/adr/` on that branch.
- `.github/workflows/adr-lint.yml` added (ported from `docs/qm/
  project-seed/ci/adr-lint.yml`, glob path adjusted for this project's
  `docs/qm` mount point vs. the seed's assumed `governance/qm`).
- Doc references updated from `docs/adr/` to `docs/qm/adr/`:
  `docs/architecture.md`, `docs/api.md`, `docs/llm/ARCHITECTURE.md`,
  `web/src/layout/panel_registry.ts`.
- Submodule pin lands on `project/codecartographer`'s current tip
  (`d8affe4`), which already includes today's new
  `DRAFT-verify-actual-consumption-before-editing.md` ADR.

## 2. Dead root `requirements.txt` [DONE 2026-07-21]

**Status: done.**

Deleted outright — nothing installs from it. The real Docker build
(`docker-compose.yml`'s `CODECARTO_PATH=./codecarto` override) installs
from `codecarto/requirements.txt` instead; CI uses `pip install
-e ".[dev]"` against `pyproject.toml` directly. A repo-wide grep for
`requirements.txt` outside `docs/qm/` turns up exactly this file and
the `Dockerfile` line that (via the compose override) doesn't even
point at it.

## 3. Pillow CVE unpatched in the real dependency tree [DONE 2026-07-21]

**Status: done.**

`uv.lock` had Pillow pinned at 12.1.0 (transitive via `matplotlib`).
Several open high-severity CVEs (heap out-of-bounds write, OS command
injection via `WindowsViewer.get_command()`) are patched at 12.3.0.
`uv lock --upgrade-package pillow` resolves cleanly to 12.3.0 with no
other package versions moved; verified `codecarto.main` still imports
and boots (63 routes) against the updated lock.

## 4. `pyproject.toml` dependency-declaration audit

**Status: pending.**

- `motor` (`pyproject.toml:38`) — declared, never imported anywhere in
  `codecarto/`. The real Mongo driver in use is `pymongo`, imported
  directly in `codecarto/services/cache_service.py:129` but **not**
  declared in `pyproject.toml` (works today only because something else
  pulls it in transitively).
- `pytest-asyncio` (`pyproject.toml:39`) — sits in the main
  `dependencies` list; it's a test-only dependency (exercised via
  `asyncio_mode = "auto"` for `tests/test_*.py`) and belongs in the
  `dev` extra instead.
- `mpld3`, `scipy`, `importlib-metadata`, `python-multipart` — no
  direct `import` found in `codecarto/`. **Not removed on a grep alone**
  — each gets a live check (temporarily drop it, `uv lock && uv sync`,
  run the full `pytest` suite, boot `codecarto.main`) before being
  either removed or kept-with-a-stated-reason. `scipy` in particular is
  a plausible false positive: NetworkX's `spectral_layout`/
  `kamada_kawai_layout` (used by `graph_serializer.py` per project
  history) import `scipy` internally without `codecarto` ever writing
  `import scipy` itself.

## 5. Orphaned backend parser files

**Status: pending.**

- `codecarto/services/parsers/python/__init__.py` — empty (0 bytes),
  the sole remaining file in that package, nothing imports the package.
- `codecarto/services/parsers/ASTs/python_list_ast.py` (503 lines) —
  entirely the `PythonListAST(BaseASTVisitor)` class, never imported or
  instantiated anywhere. Only `PythonCustomAST` (same directory) is the
  live engine behind every Python parse.

## 6. Stale `moe` CORS origin in `main.py`

**Status: pending.**

`codecarto/main.py:22-27` carries a `# TODO: this is here to test moe
calling the api` comment and a `http://localhost:5000  # moe` CORS
origin, predating `graphbase` being embedded as an in-process submodule
(`graphbase` was extracted from the standalone `quaternionmedia/moe`
service per `graphbase/README.md:14`). `graphbase` now runs in-process
under `/db`, so the cross-origin allowance for a standalone "moe" server
looks stale.

## 7. Dead frontend files (pre-`features/` refactor duplicates)

**Status: pending.**

- `web/src/components/codecarto/upload/upload_nav.ts`(+`.css`) —
  superseded by `features/upload/components/UploadNav.ts`.
- `web/src/components/codecarto/url_input/url_input.ts`(+`.css`) —
  superseded by `features/repository/components/UrlInput.ts`.
- `web/src/components/codecarto/directory/directory_nav.ts`'s
  `DirectoryNav` component export specifically (its
  `DirectoryNavController` class is still live) — superseded by
  `features/repository/components/DirectoryNav.ts`.
- `web/src/features/graph/components/plot/plot.ts`(+`.css`) — an
  orphaned duplicate of `features/graph/components/Plot.ts`, the one
  actually re-exported/used via `features/graph/index.ts`.
- `web/src/features/graph/components/GraphControls.ts` — exported from
  `features/graph/index.ts` but never consumed by any panel.
- `web/src/components/codecarto/debug/Debug.ts` (+ its exclusive
  `debug.css`, `tracer.css`) — completely unmounted; `src/index.ts:41`
  has the mount call commented out (`// Tracer(cells);`).
- `web/src/services/demo_service.ts` and the barrel
  `web/src/services/index.ts` — nothing imports the barrel, and
  `demo_service.ts` is only reachable through it.

(Confirmed separately: the June-27-flagged dead code —
`PlotService.plotCFile`/`plotCDirectory` and several `actions.ts`
wrappers — was already removed via PR #70. Not part of this queue.)

## 8. Dead `actions.ts` methods

**Status: pending.**

`web/src/state/actions.ts`: `PlotActions.plotUnified` (:438-464, zero
callers — only `PlotService.plotUnified` is called, from `loadDemo`/
`plotUploadedFile`), `RepoActions.clearRepository` (:584-586, zero
callers), `RepoActions.selectFile` / `UploadActions.selectFile`
(:577-579, :598-600, zero callers anywhere).

## 9. Unused `web/package.json` dependencies

**Status: pending.**

`meiosis` (never imported directly), `d3-force` (never imported
directly — `d3`'s meta-package already pulls it transitively),
`meiosis-tracer` (only consumer is item 7's `Debug.ts` — becomes
genuinely unused once that's removed).

## 10. `docs/api.md` drift

**Status: pending.**

- Palette section (api.md:595-604) documents a **different API than
  what's implemented**: `GET /palette/list` and `GET /palette/{id}`
  don't exist. Real routes (`codecarto/routers/palette_router.py:8,26`)
  are `GET /palette/default` and `GET /palette/custom?palette_id=`,
  different response shapes entirely.
- Undocumented live endpoints: the entire `/lexicon/*` router
  (`GET /lexicon/`, `/{language}`, `/{language}/graph`,
  `/{language}/index` — `lexicon_router.py:24-54`, registered
  `main.py:53`), `GET /c-parser/visualizer` (`c_parser_router.py:368`),
  and most of `/pam/*` (`GET /pam/history`, `/pam/sessions`,
  `/pam/sessions/{session_id}`, `WS /pam/ws/replay` —
  `pam_router.py:209-394`).

## 11. `docs/services.md` drift

**Status: pending.**

Documents deleted/nonexistent files: `parser_service.py`,
`palette_service.py`, `parsers/python/directory_parser.py`,
`parsers/python/dependency_parser.py`, `polygraph_service.py` (all
deleted in the June 27 cleanup or earlier). Omits the real current
services entirely: `cache_service.py`, `lexicon_service.py`,
`unified_parser_service.py`, `c_parser_service.py`.

## 12. `.github/CONTRIBUTING.md` drift

**Status: pending.**

- Testing section (lines 327-338) documents `npm run test:e2e`,
  `npm run test:e2e:ui`, `npx playwright test ...`. `web/package.json`
  has only `"build"` and `"dev"` scripts — no Playwright dependency at
  all.
- "Feature-Based Frontend Structure" (lines 62-91) describes a
  Mithril-component pattern that predates the Golden Layout shell
  described in `docs/architecture.md`; the referenced files still
  exist, so it isn't fully invented, but it conflicts with current
  architecture docs and omits the now-primary `web/src/layout/`
  structure.

---

## Held for explicit go-ahead (not part of the branch's own commits)

- `data/graphs.db` (repo root, 135KB SQLite, tables `nodes`/`edges`/
  `graphs`/`views`/`user_actions`/`user_preferences` with tiny sample
  data) — added once 2026-03-03, never touched since, referenced by
  nothing in `codecarto/` (the real `data/` references in code are
  `codecarto/data/lexicons/` and `codecarto/data/c_stubs/`, a different,
  nested directory).
- 8 stale remote branches: 6 fully merged
  (`c-parser-stub-headers-phase1`, `caching-and-parser-consolidation`,
  `consolidate-68-69-70-71`, `followup-lifts-completion`,
  `local-directory-path-hookup`, `uv-refactor`), 2 superseded with
  their content already on `main` via a different branch
  (`feat/gh-auth-schema` → superseded by PR #75's branch;
  `copilot/frontend-integration-golden-layout` → superseded, its
  commit message matches one already in `main`'s history).

## Status

In progress — see checkmarks above as this branch lands each commit.
