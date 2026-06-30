# Parser consolidation lifts and other scope drift

Survey of the codebase (2026-06-28) for places where logic should be
*lifted* into a shared abstraction to combine duplicated parser code, and
other places where a router/service has accreted concerns beyond its
original scope.

Each finding has file:line references, a concrete reproduction of the
duplication/drift, and a suggested direction. Ranked roughly by impact
within each category.

**Status (2026-06-29): everything in this document is now implemented.**
1.1 shipped 2026-06-28 (see its own section — the real picture turned out
different from the initial survey finding). 1.2/1.3/2.1/2.3 were
implemented by PR #70 (`copilot-swe-agent`) on `caching-and-parser-consolidation`
and verified+cherry-picked here (see each section for what was checked and
what tests were added — the original PR shipped zero tests). 1.4 and 2.2
were implemented in this same pass. Branch: `followup-lifts-completion`.

---

## 1. Parser-combination lifts

### 1.1 `ParserService` was a second wrapper around shared engines — consolidated [DONE 2026-06-28]

**Impact: medium (revised down from the original "high" estimate — see below). ~430 lines deleted, 1 new capability added (real dependency-graph resolution in the unified pipeline).**

The original survey claimed `PythonCustomAST`/`python_list_ast.py`/
`base_ast.py` were a wholly separate legacy stack alongside
`python_language_parser.py`. **That was wrong** — `python_language_parser.py`
already wraps `PythonCustomAST` directly (it's the live AST engine behind
*every* Python parse in the unified pipeline, not a legacy leftover). The
actual duplication was narrower: `ParserService`
([parser_service.py](../../../codecarto/services/parser_service.py), now
deleted) was a *second, thinner* wrapper around the same engine, plus two
genuinely standalone parsers with no unified-pipeline equivalent:

- `parse_code_directory()` → `PythonCustomAST` directly, redundant with
  `python_language_parser.py`'s own wrapping of the same class.
- `parse_directory()` → `DirectoryParser` (`parsers/python/directory_parser.py`,
  61 lines) — functionally identical to `UnifiedParserService.build_graph(depth=1)`.
- `parse_dependancy()` → `DependencyParser`
  (`parsers/python/dependency_parser.py`, 162 lines) — resolved real
  file-to-file import edges (with external stdlib/third-party nodes). **The
  unified pipeline had no equivalent at all** — it only emitted per-statement
  `import` nodes, never resolved to an actual target file.

Two real call sites used this, not one: `plotter_router.py`'s `/demo`
endpoint (live "⚡ Load Demo" button) **and** `cli.py`'s
`codecarto repo graph` command (also independently bypassed `ParserService`
for its own "ast" mode, calling `PythonCustomAST` directly a *third* way).
Also discovered mid-implementation: the demo's "ast"/"dependencies" UI
buttons were never actually wired up frontend-side
(`actions.ts`'s `loadDemo()` always sent the `directory` default) — so the
"dependencies" mode was only ever reachable via a direct `POST /demo` API
call, not through the UI.

**What shipped**, after asking which way to resolve the dependency-mode gap
(chose: build a real equivalent rather than drop the feature or leave it on
a separate path):

- `python_language_parser.py` gained `extract_python_imports(raw) -> list[str]`
  — a clean, standalone `ast`-module-based import extractor (independent of
  `PythonCustomAST`'s own import bookkeeping, which tracks per-file
  last-write-wins state unsuitable for cross-file resolution).
- `unified_parser_service.py` gained `_add_python_dependency_edges()`, run
  once at the end of `build_graph()` (renamed from `_build_graph`, made
  public — `cli.py` now calls it directly for the raw graph) whenever
  `depth >= 2`. Resolves each file's imports to a `depends_on` edge: to
  another file's depth-1 node when it's part of the same parse, or to a
  synthetic `external_module` node (one per top-level package, e.g.
  `external::requests`) otherwise. New edge kind `depends_on` and node kind
  `external_module` documented in `language_parser.py`'s module docstring.
  Verified live: parsing `codecarto/` itself now produces 48 distinct
  `external_module` nodes and real internal `depends_on` edges.
- `/demo` now calls `get_local_repo()` + `UnifiedParserService.parse()`
  directly — `directory` mode → depth=1, everything else → depth=2 (which
  now includes both symbols *and* dependency edges together, matching how
  the rest of the app already treats depth=2 as "the combined view," no
  separate symbols-only/deps-only mode).
- `cli.py`'s `repo graph` command (`-t ast|directory|dependency`) now routes
  all three through `UnifiedParserService.build_graph()` too — `ast` and
  `dependency` produce the same output now, for the same reason.
- Deleted entirely (zero remaining callers, confirmed via repo-wide grep):
  `parser_service.py`, `parsers/python/directory_parser.py`,
  `parsers/python/dependency_parser.py`, and `palette_service.py` (its only
  caller, `/demo`'s `apply_styles()` call, is what made it dead — the file's
  own docstring already called it "OLD CODE").
- **Not** deleted, because they're load-bearing: `PythonCustomAST`,
  `python_list_ast.py`, `base_ast.py` — still the live engine behind
  `python_language_parser.py` for every Python repo, demo included.

**Update (2026-06-28, later same day): extended to the GitHub-streaming
path too.** The resolution core was factored out into a pure
`_resolve_python_dependencies(file_id_by_stem, raw_by_file_id)` (no closure
state, easily testable) that both `_add_python_dependency_edges`
(non-streaming, mutates an `nx.DiGraph` in place) and `stream_parse_url`
now call. `stream_parse_url`'s phase 2 collects each Python file's raw
content into `python_raw_by_file_id` as files arrive (can't resolve
per-file — an earlier-completing file's import target might not have
streamed yet), then once the main fetch/parse loop finishes, resolves and
emits the resulting `depends_on` edges and `external_module` nodes as one
final batch of SSE events — same "defer until the full set is known"
approach C's cross-file `calls` edges already use in the
`batch_whole_tree` path. SSE events have no `graph.has_edge()` to dedupe
against (unlike the in-memory path), so dedup is explicit via a `seen_edges`
set. Verified live against `pypa/sampleproject`: a real cross-file edge
(`tests/test_simple.py -> sample/simple.py`) plus 3 external module nodes
(`os`, `nox`, `unittest`) resolved correctly through the live streaming
endpoint.

**Known limitation still carried forward:** dependency-edge resolution is
stem-based (matches the unified pipeline's existing `file::{parent_dir}/{name}`
id scheme, not a full repo-relative path) — two files sharing a stem (e.g.
two different packages' `__init__.py`) can't be disambiguated; the
last-visited one wins. Pre-existing characteristic of this id scheme, not
newly introduced, and not addressed by this update.

### 1.2 `batch_whole_tree` dispatch-splitting logic is duplicated, not shared [DONE 2026-06-29]

**Impact: medium — same ~15-line algorithm reimplemented twice with different data shapes.**

**Shipped via PR #70, exactly as suggested below**: `_split_by_batch_mode(items, ext_of)`
in `unified_parser_service.py`, used by both `stream_parse_url` and
`_walk_folder` (the latter restructured into two passes: collect file
nodes, then split-and-dispatch). PR #70 added no tests; added 5 direct
unit tests (`TestSplitByBatchMode` in `test_unified_parser_service.py`) —
pure function, no I/O, exactly as easy to test in isolation as hoped.
Confirmed no regression: all pre-existing `TestCBatchWholeTree` end-to-end
tests still pass unchanged.

Both code paths in `unified_parser_service.py` need to split a list of
files into "dispatch one-at-a-time" vs "dispatch as one batch per parser"
groups (the latter for parsers like C that need the whole file set at once
for cross-file references — see `LanguageParser.batch_whole_tree`).

- **GitHub-streaming path** — `stream_parse_url`'s inline split
  ([unified_parser_service.py:405-420](../../../codecarto/services/unified_parser_service.py#L405-L420)):
  ```python
  per_file: list[tuple[str, str, str, object]] = []
  batched: dict[int, tuple[object, list[tuple[str, str, str]]]] = {}
  for folder_name, file_name, dl_url in parseable:
      ext = Path(file_name).suffix.lower()
      parser = ParserRegistry.get(ext)
      if parser is None: continue
      if getattr(parser, "batch_whole_tree", False):
          key = id(parser)
          if key not in batched: batched[key] = (parser, [])
          batched[key][1].append((folder_name, file_name, dl_url))
      else:
          per_file.append((folder_name, file_name, dl_url, parser))
  ```
- **Local-directory path** — `_walk_folder`'s inline split
  ([unified_parser_service.py:582-590](../../../codecarto/services/unified_parser_service.py#L582)),
  same `getattr(parser, "batch_whole_tree", False)` / `id(parser)`-keyed
  dict pattern, just walking a `Folder` tree and keying by `(File, file_id)`
  pairs instead of `(folder_name, file_name, dl_url)` tuples.

The actual *parse-and-merge* logic downstream is legitimately different
(one formats SSE event strings via `node_events_for`, the other merges into
an `nx.DiGraph` via `_merge_batch_subgraph`) — that part shouldn't be
forced together. But the **grouping step itself** is identical in shape and
could be one generic helper:

```python
def _split_by_batch_mode(items: Iterable[T], ext_of: Callable[[T], str]) -> tuple[list[tuple[T, parser]], dict[int, tuple[parser, list[T]]]]:
    ...
```

**Suggested direction:** extract the grouping into a shared helper in
`unified_parser_service.py` or `language_parser.py`, parameterized over how
to extract the extension from an item. Low risk — it's pure grouping logic
with no I/O, easy to unit test in isolation from the two call sites' very
different downstream handling.

### 1.3 Functional parity gap between the two C parsing entry points (`-I<project root>`) [DONE 2026-06-29]

**Impact: medium — silently wrong output for multi-directory C projects parsed via the generic path, not just a style issue.**

**Shipped via PR #70**: `c_language_parser.py`'s `parse_files` now tracks
real on-disk paths separately, computes `os.path.commonpath` over them,
and passes the result (or its parent, if commonpath itself resolves to a
single file rather than a directory) as `project_root` to
`default_parse_args`. PR #70 added no tests; live-verified by hand before
trusting it — built a real multi-directory project (`foo.h` at the root,
`foo.c`/`main.c` in `src/`, `#include "foo.h"` only resolvable via
`-I<root>`), confirmed the OLD code fails (`libclang: 'foo.h' file not
found`, zero `calls` edges) and the NEW code resolves it correctly
(`main -> foo_fn` edge present). Added 3 regression tests
(`TestCLanguageParserProjectRoot` in `test_c_parser_service.py`), including
the single-file commonpath-returns-a-file-not-a-dir edge case.

There are two independent entry points into `CParser`, and they don't pass
the same compiler args:

- `c_parser_service.py`'s `parse_directory`
  ([c_parser_service.py:213-214](../../../codecarto/services/c_parser_service.py#L213-L214))
  — used by the dedicated `/c-parser/*` endpoints — calls:
  ```python
  extra_args=default_parse_args(project_root=dir_path)
  ```
- `c_language_parser.py`'s `parse_files`
  ([c_language_parser.py:163-166](../../../codecarto/services/parsers/c_language_parser.py#L163-L166))
  — used by the generic `/parse/unified`, `/parse/stream`,
  `/parse/stream-url` paths for any C/H file, **including locally-walked
  real directories where a project root is fully knowable** — calls:
  ```python
  extra_args=default_parse_args()  # no project_root
  ```

`default_parse_args(project_root=...)` exists specifically to add
`-I{project_root}` because "multi-directory C projects commonly do
`#include "foo.h"` expecting the build's `-I.` root include, not just the
including file's own directory" (its own docstring,
[c_parser.py:62-65](../../../codecarto/services/parsers/c_parser.py#L62-L65)).
Parsing the *same* multi-directory C project through the unified pipeline
(e.g. selecting a local C repo in the Source tab and plotting it) will miss
those includes; parsing it through `/c-parser/directory` will not. This is
a behavior difference caused by the architectural split, not an
intentional design choice — nothing in `c_language_parser.py`'s comments
suggests omitting `project_root` was deliberate.

**Suggested direction:** `c_language_parser.py`'s `parse_files` does have
the files' real disk paths available when they're local (`f.url`, checked
at line 152-154) — their common ancestor directory could be computed and
passed through as `project_root`. For GitHub/virtual files there's no real
project root, so the current no-arg call stays correct for that branch.

### 1.4 (Minor) Recursive Folder-tree walking reimplemented at ~4 call sites [DONE 2026-06-29]

**Impact: low — small, but a `Folder.walk_files()` method would remove repetition.**

Added `Folder.iter_files() -> Iterator[tuple[Folder, File]]`
(`models/source_data.py`) and collapsed the 3 genuine matches:
`_collect_parseable` and `_add_python_dependency_edges`
(`unified_parser_service.py`), `_fetch_content_for_folder`'s `collect()`
(`github_service.py`). `parser_service.py`'s `read_directory_recursive`
no longer exists (deleted in 1.1). Deliberately did **not** touch
`_walk_folder`'s own recursion — on closer look it builds graph nodes/
edges with per-level parent-id/depth context as it descends, which isn't
actually a "give me a flat list of files" pattern; forcing it through this
iterator would be a worse fit, not a cleaner one. 5 new tests
(`test_source_data.py`).

---

## 2. Other scope drift

### 2.1 SSE cache-replay block duplicated verbatim across two router endpoints [DONE 2026-06-29]

**Impact: medium — ~25 identical lines, the kind of duplication that silently diverges on the next edit.**

**Shipped via PR #70, exactly as suggested below**: `_stream_cached_graph(cached, layout)`
in `unified_parser_router.py`, called from both `stream_parse` and
`stream_from_url`. PR #70 added no tests; added `test_unified_parser_router.py`
covering the generator directly (event order, depth-sort, `from_cache`
marking, malformed-entry handling) plus an end-to-end test that actually
proves the point of the extraction — `/parse/stream` and `/parse/stream-url`
produce **byte-for-byte identical** SSE output for the same cached entry.

`unified_parser_router.py` has two nearly byte-for-byte identical inner
functions for replaying a cached graph as SSE:

- `stream_parse`'s `stream_cached()`
  ([unified_parser_router.py:175-199](../../../codecarto/routers/unified_parser_router.py#L175-L199))
- `stream_from_url`'s `stream_cached_url()`
  ([unified_parser_router.py:257-281](../../../codecarto/routers/unified_parser_router.py#L257-L281))

Both: flatten `cached["graph"]["nodes"]` from `{id: {...}}` dict form to a
flat list merging in `metadata`, build the same `meta` event payload, yield
`meta` → sorted `node`s → `edge`s → `done`, with identical
`await asyncio.sleep(0)` cooperative-yield placement. The frontend already
solved the analogous problem correctly — `PlotService._consumeSSE()`
(`plot_service.ts`) is one shared parser used by all three
`streamUnified`/`streamFromUrl`/`streamCGithub` callers. The backend has no
equivalent for the cache-replay side.

**Suggested direction:** extract a single
`_stream_cached_graph(cached: dict, layout: str) -> AsyncIterator[str]`
(module-level in `unified_parser_router.py`, or a method on
`UnifiedParserService`) and call it from both endpoints.

### 2.2 Thread → `asyncio.Queue` → SSE bridge hand-rolled independently twice [DONE 2026-06-29]

**Impact: low-medium — same wiring pattern, not literally copy-pasted, so a shared helper needs to fit both shapes.**

**Shipped**: new `codecarto/util/threaded_feeder.py` —
`start_threaded_feeder(worker_factory)` creates the queue, captures the
running loop, and starts the daemon thread; `worker_factory(queue, loop)`
returns the zero-arg thread target, accommodating both call sites' very
different worker shapes (one fully closure-based, one taking a log path)
without forcing either into an awkward signature. `pam_router.py`'s
`_tail_thread`/`_journald_thread` became inline closures built by a
factory inside `on_pam_startup` rather than top-level functions taking
explicit `(queue, loop)` args — preserves the "no log file found" fallback
exactly (`_event_queue` still gets a real, just unfed, `Queue`). 5 new
direct unit tests (`test_threaded_feeder.py`); live-verified
`on_pam_startup()` against a real `PAM_LOG_FILE` and the "no log available"
path; existing `/c-parser/stream-github` test coverage
(`test_c_parser_router.py`) passes unchanged.

`c_parser_router.py`'s `/stream-github`
([c_parser_router.py:170-203](../../../codecarto/routers/c_parser_router.py#L170-L203))
and `pam_router.py`'s log tailer
([pam_router.py:115-202](../../../codecarto/routers/pam_router.py#L115-L202))
both spawn a daemon `threading.Thread` running blocking/CPU-bound work,
and feed an `asyncio.Queue` from inside that thread via
`asyncio.run_coroutine_threadsafe(queue.put(...), loop)` so the request
coroutine can `await queue.get()`. `c_parser_router.py`'s own comment
explicitly calls out the duplication: *"same pattern as pam_router.py's log
tailer"* (line 175) — it was named, not lifted.

The two aren't identical: `c_parser_router`'s is one-shot (one thread per
request, ends on a `__done__` sentinel), `pam_router`'s is a long-running
singleton broadcasting to multiple SSE sessions (ends only on
`__error__`). A shared helper would only cleanly capture the
thread-spawn + queue-feed wiring (~8 lines), not the consumption loop —
still worth it given it's the part most likely to have a subtle bug (e.g.
forgetting `daemon=True`, or capturing `loop` before thread start).

**Suggested direction:** a small `start_threaded_feeder(target, *args) -> asyncio.Queue`
helper that creates the queue, captures the running loop, and starts the
daemon thread, returning the queue for the caller to drain however it
needs. Lower priority than 2.1 — the win is smaller and the two call sites'
draining logic genuinely differs.

### 2.3 Frontend: confirmed-still-present dead `actions.ts` methods [DONE 2026-06-29]

**Impact: low — already identified in a previous session ([memory: Architectural Unification Pass](../ARCHITECTURE.md)), re-verified here, still not removed.**

**Shipped via PR #70.** Re-verified via repo-wide grep after cherry-picking:
zero remaining references to `UIActions`, `adaptCGraphToGJGF`, `plotCFile`,
`plotCDirectory`, or `clearUploads` anywhere in `web/src`. Frontend build
(`npm run build`) passes cleanly.

Zero call sites anywhere in `web/src` (checked via grep for
`actions.<ns>.<method>(` across all components) for:

- `PlotService.plotCFile` / `PlotService.plotCDirectory` (`plot_service.ts`)
  and their `actions.ts` wrappers `plotCFile`/`plotCDirectory`
- `actions.ts`'s `clearUploads()`, `toggleControlPanel()`, `setActiveTab()`
  (note: a *different*, actively-used `setActiveTab` closure exists inside
  `control_panel.ts` itself — only the `actions.ts` copy is dead)
- `actions.ts`'s `clearError()` (a same-named but unrelated
  `clearError()` function in `utility.ts`, used by `state_controller.ts`,
  is live — don't confuse the two)

Likely leftover from the Tools-tab removal mentioned elsewhere in
`ARCHITECTURE.md`. Safe to delete; out of scope for this survey since it's
already-known dead code rather than newly-discovered drift, listed here
only to keep one place that confirms it's still true as of 2026-06-28.

---

## Status: all items shipped

1. ~~**1.1**~~ — done 2026-06-28 (`caching-and-parser-consolidation`).
2. ~~**1.2, 1.3, 2.1, 2.3**~~ — implemented by PR #70
   (`copilot/frontend-integration-golden-layout`, `copilot-swe-agent`),
   verified and cherry-picked clean onto `followup-lifts-completion`
   2026-06-29. PR #70 itself also carries an unrelated Golden Layout
   frontend integration mixed into the same branch — only the
   "followups" commit (`d0e685f`) was cherry-picked; the Golden Layout
   work is a separate concern not covered by this survey.
3. ~~**1.4, 2.2**~~ — implemented 2026-06-29, same branch.

Every item shipped with tests added in this pass (PR #70's own commit had
none) and either a live manual verification or a full-suite pass
confirming no regression. Nothing outstanding from this survey as of
2026-06-29.
