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

## 4. `pyproject.toml` dependency-declaration audit [DONE 2026-07-21]

**Status: done.** Live-verified, not just grep-trusted (per this
session's own `DRAFT-verify-actual-consumption-before-editing.md` ADR):
dropped all 5 candidates at once, `uv lock && uv sync`, ran the full
`pytest` suite. Result: **4 failures**, all
`ModuleNotFoundError: No module named 'scipy'` inside NetworkX's
`spring_layout` → `to_scipy_sparse_array` (`codecarto` never writes
`import scipy` itself, but NetworkX does internally) — confirming the
suspected false positive. Restored `scipy` alone, re-ran: 293 passed, 23
skipped, 0 failures; live-booted `codecarto.main` after (63 routes,
clean).

- **Removed**: `motor` (declared, never imported — the real Mongo
  driver is `pymongo`, imported directly in `codecarto/services/
  cache_service.py:129` but previously undeclared) → replaced with an
  explicit `pymongo>=4.6` dependency. `mpld3`, `importlib-metadata`,
  `python-multipart` (no import found anywhere, live-verified safe to
  drop).
- **Moved**: `pytest-asyncio` from the main `dependencies` list into
  the `dev` extra (test-only, exercised via `asyncio_mode = "auto"`).
- **Kept**: `scipy` — genuinely load-bearing, just not via a direct
  `codecarto` import.

## 5. Orphaned backend parser files [DONE 2026-07-21]

**Status: done.** Re-verified before deleting (fresh grep for
`PythonListAST` found only its own definition file); `pytest` full
suite green after (293 passed).

- `codecarto/services/parsers/python/__init__.py` — empty (0 bytes),
  the sole remaining file in that package, nothing imports the package.
- `codecarto/services/parsers/ASTs/python_list_ast.py` (503 lines) —
  entirely the `PythonListAST(BaseASTVisitor)` class, never imported or
  instantiated anywhere. Only `PythonCustomAST` (same directory) is the
  live engine behind every Python parse.

## 6. Stale `moe` CORS origin in `main.py` [DONE 2026-07-21]

**Status: done.**

`codecarto/main.py:22-27` carries a `# TODO: this is here to test moe
calling the api` comment and a `http://localhost:5000  # moe` CORS
origin, predating `graphbase` being embedded as an in-process submodule
(`graphbase` was extracted from the standalone `quaternionmedia/moe`
service per `graphbase/README.md:14`). `graphbase` now runs in-process
under `/db`, so the cross-origin allowance for a standalone "moe" server
looks stale.

## 7. Dead frontend files (pre-`features/` refactor duplicates) [DONE 2026-07-21]

**Status: done.** Re-verified each before deleting (fresh greps, plus
traced `DirectoryNav`/`GraphControls` barrel re-exports specifically to
confirm `features/repository/index.ts`'s `DirectoryNav` export points
at the *live* `features/repository/components/DirectoryNav.ts`, an
unrelated same-named symbol — not the dead one in `directory_nav.ts`).
`directory_nav.ts` trimmed to just the still-live
`DirectoryNavController` (its exclusive `directory_nav.css` removed
too — confirmed no other file references those classes).
`features/graph/index.ts`'s now-dead `GraphControls` re-export removed.
`npm run build` clean after (765 modules, down from 779).

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

## 8. Dead `actions.ts` methods [DONE 2026-07-21]

**Status: done.** Re-verified zero callers for all four (fresh grep for
each call pattern) before removing. Removing `RepoActions.selectFile`/
`UploadActions.selectFile` left their sole backing methods —
`state_controller.ts`'s `setSelectedRepoFile`/`setSelectedLocalFile` —
newly orphaned (confirmed via repo-wide grep, no other callers);
removed those too in the same commit rather than leave fresh dead code
behind, a small scope extension beyond the original finding. `npm run
build` clean after.

## 9. Unused `web/package.json` dependencies [DONE 2026-07-21]

**Status: done.** Re-verified all three unused after item 7 landed
(fresh grep, zero direct imports). `npm install` only removed 2
packages from `node_modules` — `d3-force` stays installed as `d3`'s own
transitive dependency, as expected. `npm run build` clean after.

## 10. `docs/api.md` drift [DONE 2026-07-21]

**Status: done.** Read `palette_router.py`/`plot_data.py` directly to
get the real `Palette` shape and `fetch_palette_by_id`'s placeholder
status right, not just the route paths. Added the `/lexicon/*` section
with a pointer to `docs/llm/roadmap/lexicon.md` (this is real,
roadmapped infrastructure — documenting it is in scope even though it's
not wired to the frontend yet).

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

## 11. `docs/services.md` drift [DONE 2026-07-21]

**Status: done.** Read each real service's actual public methods
directly before documenting them (not just filenames). Also found and
fixed a related staleness while in this file: the "GitHub Token"
section still described the pre-ADR hand-rolled `/run/secrets/
github_token`-only lookup, superseded by `resolve_github_token()`
(keyring-first — see `docs/qm/adr/DRAFT-github-token-resolution.md`).

Documents deleted/nonexistent files: `parser_service.py`,
`palette_service.py`, `parsers/python/directory_parser.py`,
`parsers/python/dependency_parser.py`, `polygraph_service.py` (all
deleted in the June 27 cleanup or earlier). Omits the real current
services entirely: `cache_service.py`, `lexicon_service.py`,
`unified_parser_service.py`, `c_parser_service.py`.

## 12. `.github/CONTRIBUTING.md` drift [DONE 2026-07-21]

**Status: done.** Also caught, while fixing this: the frontend
structure example still listed `GraphControls.ts` — deleted earlier on
this same branch (item 7) — as a live file. Fixed alongside the
Golden-Layout-shell pointer to `docs/architecture.md`.

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

## Held items — both approved and executed 2026-07-21

- `data/graphs.db` — deleted (this branch's final commit).
- 8 stale remote branches — deleted directly on
  `quaternionmedia/codecartographer` (not a branch commit): 6 fully
  merged (`c-parser-stub-headers-phase1`,
  `caching-and-parser-consolidation`, `consolidate-68-69-70-71`,
  `followup-lifts-completion`, `local-directory-path-hookup`,
  `uv-refactor`), 2 superseded with their content already on `main` via
  a different branch (`feat/gh-auth-schema`, `copilot/frontend-
  integration-golden-layout`).

## Status: all 12 items shipped

All items landed on `cleanup/2026-07-21-full-review`, one commit each,
each re-verified live (not grep-trusted alone) before landing — per
this session's own `DRAFT-verify-actual-consumption-before-editing.md`
ADR. Two items surfaced *during* execution that weren't in the original
survey and were folded into the relevant commit rather than left
behind: `state_controller.ts`'s `setSelectedRepoFile`/
`setSelectedLocalFile` (orphaned by item 8's edit) and the GitHub Token
section of `docs/services.md` (found stale while fixing item 11).

Full branch verification: `pytest` full suite (293 passed, 23 skipped,
0 failed), `npm run build` clean, and a live boot check
(`uvicorn codecarto.main:app`, `/openapi.json` + `/docs` both 200).

Still open, held for explicit go-ahead (see "Held for explicit
go-ahead" above) — not part of this branch's commits: deleting
`data/graphs.db` and the 8 stale remote branches.

This queue doc can be moved to `docs/llm/archive/legacy/` once merged,
matching where `parser_consolidation_and_scope_drift.md` (the pattern
this doc followed) ended up.
