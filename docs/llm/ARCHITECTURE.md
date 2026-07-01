# CodeCartographer Architecture

System overview and component interactions for the CodeCartographer codebase visualization tool.

## Overview

CodeCartographer parses source code and generates interactive graph visualizations to help developers understand code structure, dependencies, and relationships.

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Graph Processing**: NetworkX
- **Visualization**: Gravis (for HTML rendering)
- **Package Manager**: uv

### Frontend
- **Framework**: Mithril.js
- **State Management**: Meiosis
- **Build Tool**: Vite
- **Visualization**: D3.js, vis-network
- **Language**: TypeScript

---

## Directory Structure

```
codecartographer/
|-- codecarto/                       # Backend Python package
|   |-- main.py                      # FastAPI application entry
|   |-- routers/
|   |   |-- unified_parser_router.py # /parse/* endpoints (all languages)
|   |   |-- plotter_router.py        # /demo + /render/html (Notebook renderer)
|   |   |-- c_parser_router.py       # C/H semantic parse endpoints
|   |   |-- repo_router.py           # GitHub + local repository tree endpoints
|   |   `-- pam_router.py            # PAM auth log monitor
|   |-- services/
|   |   |-- unified_parser_service.py  # Unified parse orchestration
|   |   |-- graph_serializer.py        # NetworkX -> gJGF (depth-aware sizing)
|   |   |-- c_parser_service.py        # C parser service layer
|   |   `-- parsers/
|   |       |-- language_parser.py          # LanguageParser Protocol + ParserRegistry
|   |       |-- python_language_parser.py   # Python adapter (.py)
|   |       |-- c_language_parser.py        # C/H adapter (.c, .h)
|   |       |-- c_parser.py                 # libclang-based C semantic parser
|   |       |-- pam_parser.py               # PAM log parser
|   |       |-- ASTs/                       # PythonCustomAST visitor (legacy)
|   |       `-- python/                     # Legacy Python parsers
|   `-- models/
|
|-- web/src/
|   |-- components/codecarto/
|   |   `-- control_panel/    # 2-tab panel (Source / Graph)
|   |-- features/graph/
|   |   |-- services/         # Renderers: D3, Gravis, Notebook, System (PAM)
|   |   |-- config/           # Styling schema
|   |   `-- extensions/       # Graph extensions (drag, zoom, select, etc.)
|   |-- state/                # Meiosis state + PlotActions
|   `-- services/             # API service clients (PlotService, RepoService)
|
`-- docs/llm/                 # LLM-focused docs
    `-- archive/              # Historical implementation notes
```

---

## Unified Graph Architecture

### Core concept: depth-based hierarchy

All parsers produce nodes using the **unified node schema** so any renderer
can display any language without format negotiation.

| depth | meaning | node_id prefix | shape source | size multiplier |
|-------|---------|----------------|--------------|-----------------|
| 0 | directory | `dir::` | D3 fallback (diamond) | 3.0× base |
| 1 | file | `file::` | D3 fallback (square) | 1.8× base |
| 2 | top-level symbol | parser-specific | **parser-set** (`node.shape`) | 1.0× base |
| 3 | sub-symbol (arg, field…) | parser-specific | **parser-set** (`node.shape`) | 0.6× base |

### Unified node schema

```python
{
  "depth":    int,          # 0=dir, 1=file, 2=symbol, 3=sub-symbol
  "language": str,          # 'python' | 'c' | 'unknown'
  "kind":     str,          # 'directory'|'file'|'class'|'function'|'struct'|...
  "label":    str,          # human-readable name
  "file":     str,          # source file path
  "line":     int,          # source line number
  "meta":     dict,         # language-specific extras (qualifiers, param_count, etc.)
  # Visual grammar — set by the parser, read directly by the renderer:
  "shape":    str | None,   # 'circle'|'square'|'diamond'|'hexagon'|'triangle'|'ngon'|...
  "color":    str | None,   # hex colour, e.g. '#4a9eff'
}
```

> **Parser-owned visual grammar**: parsers set `shape` and `color` so that no
> language-specific logic is needed inside the renderer. Renderers fall back to their
> own depth/kind heuristics only when these fields are absent (e.g. directory/file nodes).
>
> | language | example shape mapping |
> |----------|-----------------------|
> | Python | `class`→square, `function`→hexagon, `import`→triangle |
> | C | `struct`→ngon (sides from `meta.sides`), `function`→diamond, `enum`→circle |

### LanguageParser Protocol + ParserRegistry

Each language adapter implements the `LanguageParser` Protocol and
self-registers at import time:

```python
class LanguageParser(Protocol):
    language: ClassVar[str]           # e.g. 'python'
    extensions: ClassVar[list[str]]   # e.g. ['.py']
    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph: ...

# Registered adapters (import triggers registration):
#   python_language_parser.py  ->  PythonLanguageParser  (.py)
#   c_language_parser.py       ->  CLangaugeParser        (.c, .h, .cpp, …)
```

Each adapter calls `make_node(..., shape=..., color=...)` to encode visual grammar
into the node data. To add a new language, create an adapter and import it in
`unified_parser_service.py` — no renderer changes required.

**`batch_whole_tree` (optional, default off):** `unified_parser_service.py`'s
`_build_graph`/`_walk_folder` dispatch one file at a time to a language
parser (`parser.parse_files([file], depth)`) — fine when a parser's
cross-file references don't matter, as with Python today. A parser that
sets `batch_whole_tree: ClassVar[bool] = True` (see `CLangaugeParser`)
instead gets every one of its files across the *whole* tree collected into
one `parser.parse_files(all_files, depth)` call, made after the tree walk
finishes (`_parse_pending_batches`). C needs this because cross-file `CALLS`
resolution requires the complete file set in one `CParser` call — see
"C semantic stream path" below for the full rationale, including why this
trades some streaming progressiveness for correctness.

---

## Data Flow

### Unified parse path (all languages, depth=2)

The UI always uses `depth=2` to produce a single combined graph that includes
directories, files, symbols, and dependency edges in one pass. There is no
separate mode selector — one plot shows everything.

```
User fetches repo / clicks Plot
  |
  v
PlotService.streamUnified() -> POST /parse/stream  (SSE)
  |
  v
UnifiedParserService.stream_parse(directory, depth=2, extensions?)
  |-- Walk folder tree -> depth-0 dir + depth-1 file nodes
  |-- For each file with content:
  |     ParserRegistry.get(ext) -> language parser
  |     parser.parse_files([file], depth=2) -> unified nx.DiGraph
  |        (adds depth-2 symbol nodes + dependency edges)
  |-- Compute layout (NetworkX)
  |-- Yield SSE: meta → nodes (BFS order) → edges → done
  |
  v
StreamingGraphRenderer (frontend rAF loop)
  |-- addNode() per SSE 'node' event → pop-in animation
  |-- addEdge() per SSE 'edge' event
  |-- finalize() on 'done' → fit view
  |
  v
D3 canvas: reads node.shape / node.color from parser; falls back to
           depth/kind heuristics for nodes without parser-set values
```

**File click**: clicking a file in the tree creates a single-file Directory
and streams it through the same pipeline, fetching raw content if needed.

**Auto-plot**: fetching a repository immediately triggers streaming — no
separate "Plot" button click required.

### Lazy node expansion

```
User right-clicks file node -> Expand
  |
  v
PlotService.expandNode(directory, nodeId, depth=2)
POST /parse/expand
UnifiedParserService.expand_node(directory, nodeId, depth)
-> Returns sub-graph of node + all descendants
```

### Legacy parse path (Python-only, still active)

```
POST /plotter/whole_repo  { parse_by: 'ast'|'directory'|'dependencies' }
-> ParserService -> PythonCustomAST | DirectoryParser | DependencyParser
-> GraphSerializer -> gJGF
```

### C semantic stream path (libclang, direct API path)

This path is now primarily for direct/manual callers of
`/c-parser/stream-github`. The default web control-panel flow routes C
example chips through unified `/parse/stream-url` like other languages.
Unlike the unified pipeline above, libclang parsing here is synchronous
CPU-bound work, so it runs in a background thread — the same pattern
`pam_router.py` uses for its log tailer — while the request coroutine drains
an `asyncio.Queue` the thread feeds via `asyncio.run_coroutine_threadsafe`.
This keeps the event loop responsive and lets nodes reach the client the
moment each file finishes parsing, instead of after the whole repo is done.

```
Caller posts directly to `/c-parser/stream-github` (SSE)
  |
  v
c_parser_router.stream_c_github()
  |-- threading.Thread(worker) starts:
  |     CParserService.parse_github(url, on_progress=...)
  |       |-- download + extract archive (or reuse cache)   -> 'fetching' events
  |       |-- skip platform-specific compat files            -> 'meta' event (file/skip counts)
  |       |-- CParser.parse_files(): pass 1, one file at a time
  |             each file's declarations -> on_file_parsed(file, new_nodes)
  |              asyncio.run_coroutine_threadsafe(queue.put(('nodes', ...)), loop)
  |       |-- pass 2 (cross-file CALLS) + type-edge derivation
  |             needs the COMPLETE node set, so this can't be partial
  |
  v
Request coroutine drains the queue in real time:
  |-- 'fetching'/'meta' -> forwarded as-is
  |-- 'nodes'           -> one SSE 'node' event per node, AS THE THREAD PRODUCES THEM
  |-- thread finishes    -> remap edges src/dst -> source/target, filter to known
  |                         node ids, stream as 'edge' events, then 'done'
  |
  v
StreamingGraphRenderer: same addNode/addEdge/finalize() as the unified path.
Real total node count isn't known until the thread finishes, so onFileCount's
file count is used to *estimate* a batch-size total (see
plot_service.ts's StreamCallbacks.onFileCount) — the pacing is approximate,
unlike the unified path's exact meta.nodeCount.
```

**Why nodes stream but edges don't**: pass 1 (declarations) is naturally
per-file and already looped that way before streaming existed, so exposing
it via a callback was a small change (`CParser.parse_files`'s
`on_file_parsed` param). Pass 2 (CALLS) and the derived type edges
(FIELD_OF/POINTS_TO) need to resolve symbols that may live in *other* files,
so the full node set must exist first — there's no meaningful way to stream
them earlier without risking a renderer trying to draw an edge whose
endpoint hasn't arrived yet.

### C support in the unified pipeline (`batch_whole_tree` + `unsaved_files`)

> Why, not just what: see *Unify parser/cache architecture around `ParserRegistry` + `batch_whole_tree`* ([docs/adr/DRAFT-parser-cache-unification.md](../adr/DRAFT-parser-cache-unification.md)).

Before the parser/cache unification pass, `CLangaugeParser` (the unified
adapter C registers under `.c`/`.h`/`.cpp`/…) had two bugs that made it
effectively useless for real multi-file C code:

1. **No cross-file resolution.** `_walk_folder` dispatched one file at a
   time (`parser.parse_files([file], depth)`), so `CParser`'s pass 2
   (cross-file `CALLS`) never saw more than one file — every call looked
   unresolved. Fixed by `batch_whole_tree` (see above): `CLangaugeParser`
   opts in, and `_parse_pending_batches` collects every `.c`/`.h` file
   across the *whole* tree — not just one folder — before calling
   `parser.parse_files()` once.
2. **Silently empty for any GitHub-sourced repo.** `CLangaugeParser.parse_files()`
   required `File.url` to be a real filesystem path so libclang could open
   it from disk. For local repos (`local_repo_service.py`) that's true. For
   GitHub-fetched content (`github_service.get_raw_from_repo`,
   `stream_parse_url`'s phase 2) `File.url` is a download URL and the
   content only ever exists in `File.raw` — `Path(url).exists()` is always
   False, so `paths` ended up empty and the adapter returned an empty graph,
   silently, for every single GitHub C/H file. Fixed by giving
   `CParser.parse_files()` an optional `contents: dict[path_str, text]`
   parameter, passed to libclang as `unsaved_files` — content is parsed
   from memory under a *virtual* path when no real file exists. Sibling
   `#include "x.h"` between two virtual files resolves **only if they share
   the same parent directory** in their virtual paths (libclang's
   quote-include search looks in the including file's own directory first)
   — `CLangaugeParser` uses one shared `_VIRTUAL_ROOT` for every virtual
   file in a batch specifically so this resolves. Real subdirectory
   structure is not reconstructed, so an include like `#include "sub/x.h"`
   still won't resolve for no-disk content.

**Where this plugs in for the streaming GitHub flow
(`UnifiedParserService.stream_parse_url`, phase 2):** files are split into
`batch_whole_tree` parsers (fetch everything first, parse once) vs.
everyone else (fetch-and-parse-immediately per file, as before — fully
unchanged for Python). The batch parse call is CPU-bound libclang work, so
it runs via `asyncio.to_thread` — without this, a single C-heavy repo (e.g.
CPython) would freeze the *entire server*, not just that one request, for
as long as the parse takes. Trade-off: structure (dirs/files) still streams
immediately, but C symbols for a batched extension arrive as one burst
after every file in that extension has been fetched *and* parsed — there is
currently no incremental progress signal during that gap (unlike the
dedicated `/c-parser/stream-github` endpoint above, which streams nodes
file-by-file via its background thread). Closing that gap would mean
restructuring `fetch_and_parse_batch` into something that can yield partial
progress mid-batch — not done here; flagged as a known limitation.

`has_parse_warning` is emitted as a **top-level** node attribute (not
nested under the unified schema's `meta` field) in both the unified and
dedicated C pipelines, because `graph_renderer.ts` reads
`node.has_parse_warning` directly regardless of which backend produced the
node — keeping the attribute's location consistent across pipelines was
the point, not an accident.

---

## State Management (Meiosis)

### State Structure

```typescript
ICellState {
  graphData: GraphData | null;          // Parsed graph data (gJGF)
  graphContent: m.Vnode[];              // Rendered graph elements
  graphStyling: GraphStylingOptions;    // Visual styling
  parserOptions: { fileExtensions: string[] };  // Extension filter (no mode selector)
  selectedRenderer: GraphRendererType;  // 'd3' | 'gravis' | 'notebook' | 'system'
  repo: DirectoryNavController;         // GitHub repo state
  local: DirectoryNavController;        // Local file state
}
```

### API endpoint registry (`web/src/state/api_base.ts`)

```typescript
api.parse      // /parse  (unified parser)
api.plotter    // /plotter (legacy)
api.cParser    // /c-parser
api.repoReader // /repo
```

---

## Renderer System

### Available Renderers

| type | name | auto-detect | data format |
|------|------|:-----------:|------------|
| `d3` | D3 Force Graph | yes | GraphData JSON (gJGF) |
| `gravis` | Gravis vis-network | yes | GraphData JSON (gJGF) |
| `notebook` | Notebook HTML | yes | `{ "text/html": "..." }` |
| `system` | System Monitor (PAM) | no | WebSocket events |

> Renderers are **generic engines** — they draw whatever shape/color arrives on each node.
> Language-specific visual grammar lives in the parser, not in the renderer.
> `CSemanticRenderer` exists as an unregistered opt-in tool (`canHandle()` = false).

### Renderer Selection Priority

1. User-selected renderer (`state.selectedRenderer`)
2. Metadata type (`graphData.metadata.type`)
3. Auto-detection (`canHandle(data)` loop)
4. Default fallback (D3)

### GraphNode (TypeScript)

```typescript
interface GraphNode {
  id: string;
  label?: string;
  color?: string; shape?: string; size?: number;
  x?: number; y?: number; fx?: number | null; fy?: number | null;
  // Unified schema (populated by /parse/unified):
  depth?: number;    // 0=dir, 1=file, 2=symbol, 3=sub
  language?: string; // 'python' | 'c' | 'unknown'
  kind?: string;     // 'directory' | 'file' | 'class' | 'function' | ...
  meta?: Record<string, unknown>;
  [key: string]: unknown;
}
```

---

## Parser Modes

### Unified (all languages, depth-controlled)

| `depth` | included nodes |
|---------|---------------|
| 0 | directories only |
| 1 | directories + files |
| 2 | + top-level symbols (class, function, struct, …) |
| 3 | + sub-symbols (arguments, fields, enum constants) |

**Registered languages** (auto-detected by extension):

| extension | language | adapter |
|-----------|----------|---------|
| `.py` | python | `PythonLanguageParser` |
| `.c`, `.h` | c | `CLangaugeParser` (requires `[c-parsing]` optional dep) |

### Legacy Python modes (`POST /plotter/demo` only)

`ParserService`/`PythonCustomAST`/`DirectoryParser`/`DependencyParser`
predate the unified pipeline. The only route that still exercises them is
`/plotter/demo` (the Demo button) — every other `/plotter/*` `parse_by`
entry point (`whole_repo`, `whole_repo_deps`, `folder`, `file`, `url`,
`local_directory`) was dead code (zero frontend callers) and was removed
in the parser/cache unification pass.

| `parse_by` | parser | output |
|------------|--------|--------|
| `ast` | PythonCustomAST | code structure |
| `directory` | DirectoryParser | file/folder hierarchy |
| `dependencies` | DependencyParser | import relationships |

---

## API Endpoints

| Prefix | Tag | Description |
|--------|-----|-------------|
| `/parse` | parse | **Unified parse (all languages)** |
| `/plotter` | plotter | Demo data + Notebook-renderer HTML pre-render |
| `/c-parser` | c-parser | C/H semantic parsing (libclang optional) |
| `/repo` | repo | GitHub + local repository tree operations |
| `/pam` | pam | PAM auth log monitor |
| `/palette` | palette | Color palette management |

### Unified parse endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/parse/unified` | POST | Parse a pre-fetched directory tree to given depth (blocking) |
| `/parse/stream` | POST | Same as above, streamed as SSE (`meta`/`node`/`edge`/`done`) |
| `/parse/stream-url` | POST | Fetch a GitHub repo *and* stream its parse — no separate fetch step |
| `/parse/expand` | POST | Expand a file node to reveal its symbols |
| `/parse/languages` | GET | List registered parser extensions |
| `/parse/cache` | GET | List cached parsed graphs (Cache A — see "Two C-parser caches") |
| `/parse/cache/{key}` | DELETE | Evict one cached parsed graph |

### C semantic parse endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/c-parser/file` | POST | Parse a single local C/H file (blocking) |
| `/c-parser/directory` | POST | Parse a local directory or `compile_commands.json` (blocking) |
| `/c-parser/github` | POST | Download + parse a GitHub repo's C/H files (blocking) |
| `/c-parser/stream-github` | POST | Same as above, streamed as SSE — see "C semantic stream path" |
| `/c-parser/visualizer` | GET | Standalone canvas-based C visualizer HTML |
| `/c-parser/cache` | GET | List cached extracted repos (Cache B — different cache than `/parse/cache`) |
| `/c-parser/cache/{key}` | DELETE | Evict one cached extracted repo, key = `{owner}-{repo}` |

### Two C-parser caches

`c_parser_service.py` caches two genuinely different things under
`~/.codecarto/cache/`, deliberately kept separate rather than merged into
one abstraction:

| | Cache A (`CacheService`) | Cache B (`CParserService`'s repo cache) |
|---|---|---|
| Caches | **repo source trees + parsed graphs** (Python/unified path) | **extracted source trees** (unzipped GitHub archive, C path) |
| Location | `~/.codecarto/cache/repos/{owner}-{repo}/tree.json` + `/graphs/{hash}.json` | `~/.codecarto/cache/repos/{owner}-{repo}/src/` + `metadata.json` |
| Key | repo bucket `{owner}-{repo}` (or `SHA256(url)[:16]` for non-GitHub paths), graphs further keyed by `SHA256(url+mode+layout+exts)[:16]` | `{owner}-{repo}` |
| TTL | `CC_CACHE_TTL` env var (default 24h) | same env var, same default |
| List/evict | `GET /parse/cache`, `DELETE /parse/cache/{key}` (graphs only — see `CacheService.evict_repo` for nuking a whole repo's tree+graphs) | `GET /c-parser/cache`, `DELETE /c-parser/cache/{key}` |
| Used by | `/repo/tree` (tree), `/repo/subtree` (tree, cache-first), `/repo/expand-all` (tree, cache-first), `/parse/unified`, `/parse/stream`, `/parse/stream-url`, `/c-parser/stream-github` (graphs; `/parse/stream-url` also opportunistically reads the tree cache to skip a live GitHub fetch) | `/c-parser/github`, `/c-parser/stream-github` (source tree only) |

Cache A's tree and graph caches share the same per-repo directory
(`repos/{owner}-{repo}/`) but are logically distinct: the tree cache holds
whatever `github_service.get_raw_from_repo` fetched for that repo's size
tier (full content for small repos, structure-only for medium, a shallow
single-level listing for huge/truncated repos — see `_CONTENT_FETCH_LIMIT_KB`/
`_STRUCTURE_FETCH_LIMIT_KB`), while the graph cache holds a fully parsed
result for one specific (mode, layout, extensions) combination. A tree-cache
hit only short-circuits parsing when it has full content baked in (small
repos) — `stream_parse_url` checks `directory.is_partial` and `directory.size`
before trusting it, and falls through to a live fetch otherwise.

Cache B happens to live under the same `repos/{owner}-{repo}/` bucket as
Cache A's tree cache (in a `src/` subfolder) without colliding, since they
use different filenames — kept as two caches, not merged, because a repo
cache (B) hit skips downloading+extracting the zip but still re-parses every
time (parsing isn't cached there), whereas a graph cache (A) hit skips
parsing entirely. `CParser.parse_files()` used to also support a third,
per-file pickle cache via a `cache_dir` parameter; it was never wired to a
real directory by any caller and was removed in the unification pass.

A related but distinct question — why `CacheService` and the `graphbase`
submodule's `/db/*` store stay separate despite sharing one Mongo
connection — is covered in *`CacheService` and `graphbase` stay separate
stores* ([docs/adr/DRAFT-cache-service-vs-graphbase.md](../adr/DRAFT-cache-service-vs-graphbase.md)).

---

## Compound Hierarchical Layout

> Why, not just what: see *Compound hierarchical layout (dirs → files → symbols)* ([docs/adr/DRAFT-compound-hierarchical-layout.md](../adr/DRAFT-compound-hierarchical-layout.md)).

### Goal

Each directory acts as a spatially distinct cluster: dir nodes are widely spaced, file nodes orbit their parent dir, and symbol nodes orbit their parent file. Translucent SVG circles drawn behind nodes show group boundaries.

### Backend algorithm (`compound_layout.py`)

Three-pass layout registered in `position_service.py` as `'compound_layout'`.

```
Pass 1 — dir positions
  spring_layout on dir-only subgraph, scaled by sqrt(N_dirs) * cluster_r * 1.6
  cluster_r = max_file_orbit_r + max_sym_orbit_r  (ensures no two dir clusters overlap)

Pass 2 — file orbits
  For each dir: distribute its child files evenly on a circle
  orbit radius = max(1.8, sqrt(n_files) * 0.9)  (layout units, × spread=100 → px)
  Files with no parent dir get a fallback ring centred on the origin.

Pass 3 — symbol orbits
  For each file: distribute its child symbols evenly on a circle
  orbit radius = max(0.45, sqrt(n_syms) * 0.28)
  Symbols with no parent file share a global fallback ring.
```

Parent detection: `relation='contains'` edges (primary), then `file` node attribute stem match (fallback). `graph_serializer.py`'s `spread=100` multiplier means 1.0 layout unit ≈ 100 px in the browser.

**Registration** — in `position_service.py`'s `add_custom_layouts()`:

```python
from codecarto.models.custom_layouts.compound_layout import compound_layout
self.add_layout("compound_layout", compound_layout, ["graph"])
```

`params=["graph"]` passes the full `nx.DiGraph` to the layout function (same pattern as `arch_layout`).

### Frontend bounding circles (`compound_layout.ts`)

`CompoundLayoutManager.computeGroupBounds(nodes, padding=40, baseNodeSize=4)` uses **spatial assignment** rather than edge data — each file is assigned to its nearest dir, each symbol to its nearest file. This works correctly after the backend places nodes in hierarchical orbits, and degrades gracefully if containment edges are not present in the SSE stream.

Returns `GroupBounds[]` sorted depth=0 first so SVG `<circle>` elements for dir groups are drawn before (behind) file-group circles.

Callers should guard with a layout name check — bounds are only meaningful when `compound_layout` is selected.

### SVG background circles

Both renderers insert a `<g class="compound-backgrounds">` as the **first child** of the main transform group so circles render behind links and nodes (SVG paints in document order).

| depth | fill | stroke | dash |
|-------|------|--------|------|
| 0 (dir) | `rgba(127,140,141,0.06)` | `rgba(127,140,141,0.30)` | `8,4`, width 1.5 |
| 1 (file) | `rgba(155,89,182,0.09)` | `rgba(155,89,182,0.35)` | `4,2`, width 1 |

Labels appear near the top edge of each circle. All circles fade in (300ms delay, 500ms duration) after the graph finishes rendering.

- **StreamingGraphRenderer**: `_drawCompoundBackgrounds()` is called at the end of the rAF drain loop after `_fitView()`, when both `_streamDone` and the queues are empty.
- **GraphRenderer (static)**: called after `updatePositions()` in the pre-computed position path, and on the simulation `end` event in the force-simulation path.

### UI surface

- **Graph Settings tab**: "Group Outlines" toggle → `showCompoundGroups: boolean` in `GraphStylingOptions` (default `true`). Toggling off clears the background group; toggling on redraws it without re-parsing.
- **Layout dropdown**: "Compound" is the second entry in `LAYOUT_OPTIONS` (after Spring).
- **Radial menu (node)**: "Focus Group" item appears on depth=0 and depth=1 nodes — zooms/pans the viewport to the bounding circle of that node's cluster.
- **Radial menu (canvas → Layout submenu)**: "Compound" entry triggers `onApplyLayout('compound_layout')`.

---

## GitHub Token Resolution

`github_service.resolve_github_token()` is called once at startup and cached.
Resolution order:

1. `CC_GITHUB_TOKEN` env var — project-specific, won't conflict with system
   `GITHUB_TOKEN` set by other tooling.
2. `gh auth token --hostname github.com` in a subprocess with `GITHUB_TOKEN`
   and `GH_TOKEN` **stripped** from the subprocess environment, so the `gh`
   keyring credential is used rather than a stale env var.
3. `GITHUB_TOKEN` / `GH_TOKEN` env var — legacy / Docker Compose pass-through.
4. Docker secret at `/run/secrets/github_token`.
5. Unauthenticated (60 req/h per IP; logs a warning).

**Why this order matters:** a stale `GITHUB_TOKEN` in the environment would
shadow a valid `gh` keyring token at every level if env vars were checked
first. See *GitHub token resolution order* (`docs/adr/`) for the full
rationale.

`GET /auth/github` exposes the resolved source for diagnostics. The GL header
shows a green/amber GH indicator on page load.

> **For local dev:** run `gh auth login` once. Set `MONGODB_URI` in the same
> shell that starts the server. Do not set `GITHUB_TOKEN` in `.bashrc` — use
> `CC_GITHUB_TOKEN` if you need an explicit token override that won't shadow
> the `gh` keyring.

---

## Graphbase Store (`/db/*`)

MongoDB-backed named-graph store, mounted only when `MONGODB_URI` is set.
Distinct from `CacheService` — see *CacheService and graphbase stay separate
stores* (`docs/adr/`).

Four collections in the `graphbase` database:

| Collection | What it holds | Key | Eviction |
|------------|--------------|-----|----------|
| `graph` | Named NetworkX graphs (nx.node_link_data) | `name` | Manual |
| `snapshots` | Full rendered graph (gJGF nodes + edges) | `name` | Manual |
| `bookmarks` | URL + parse settings; re-streams on load | `name` | Manual |
| `history` | Per-URL render snapshots, opt-in | `(url_hash, captured_at)` | Auto, cap 20/URL |

The frontend Graph Library panel (graphbase_panel.ts) exposes all four tiers
in one view:
- **Snapshots** — 📸 saves the live rendered graph; ▶ replays instantly
  (no re-parse) via `LayoutContext.loadGraphbaseSnapshot`.
- **Saved** — ☆ bookmarks a URL; ▶ re-streams; ★ on Recent entries that
  are already bookmarked.
- **History** — auto-appended when "Track" is on; oldest pruned at cap;
  ▶ replays any past version.
- **Recent** — the existing CacheService entries with ☆ promote-to-bookmark.

The graphbase package is a git submodule at `graphbase/`. Its public surface
is `graphbase/__init__.py` which re-exports `graphdb` (FastAPI router) and
`get_db` (lazy MongoClient) from `graphbase.src.main`. Callers in
`codecarto/` import from `from graphbase import graphdb, get_db` — not from
the internal sub-path.

---

## Code-Map Layout

The compound hierarchical layout is now four passes and source-order-aware:

- **Pass 1** — directory spring layout, X-biased (x_stretch=1.6, y_stretch=0.7)
- **Pass 2** — files orbit parent dir in equal-angle ring
- **Pass 3** — depth-2 symbols placed in a **300° source-ordered arc** around
  their file (sorted by `line` attribute, 12-o'clock = line 1 → clockwise =
  later lines). Each file cluster reads like a minimap of the source file.
- **Pass 4** — depth-3 sub-symbols orbit their nearest depth-2 parent symbol
  in the same arc convention.

`computeChildrenMap` in `compound_layout.ts` covers all four tiers for drag
propagation; dragging any node moves its entire transitive subtree.

Right-clicking a depth-≥2 node with a `line` attribute shows "◉ View Source"
in the radial menu. For GitHub repos this opens `github.com/blob/#L{line}` in
a new tab. For local paths a brief toast shows `label at file:line`.

---

## D3 Extensions

The D3 renderer supports extensions for enhanced interactivity:

- **DragExtension**: Node dragging (multi-drag, grid snap)
- **ZoomExtension**: Pan and zoom, fit-to-screen
- **SelectionExtension**: Box select, lasso select
- **HighlightExtension**: Hover with neighbor fade
- **TooltipExtension**: Rich node tooltips with metadata
- **ColorExtension**: Dynamic coloring by degree/type

---

## Known Limitations

### GL Pop-out Windows

Golden Layout 2.x supports popping panels into separate browser windows. With a Vite-bundled SPA the pop-out window loads the page URL and GL reconnects the chrome (hence the themed background is visible), but `registerComponentFactoryFunction` callbacks are bound to the **original window's Mithril instance** and are not replayed in the new window. The components therefore never mount — the pop-out shows only the GL frame with an empty content area.

For why GL is the shell at all, see *Golden Layout as the primary application shell* ([docs/adr/DRAFT-golden-layout-primary-shell.md](../adr/DRAFT-golden-layout-primary-shell.md)). For the dock panel registry and the add-window menu, see *Generalize dock panels into a registry; add a window-add menu* ([docs/adr/DRAFT-panel-registry-and-add-window-menu.md](../adr/DRAFT-panel-registry-and-add-window-menu.md)).

`popInOnClose: true` (set in `default_layout.ts`) auto-returns panels to the main window when the pop-out window is closed, so no content is permanently lost.

Fixing this properly requires implementing GL's "virtual layout" or "binding context" API so factory callbacks are re-registered in the new window's context — out of scope for the current architecture.

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `codecarto/main.py` | FastAPI app, all router registrations |
| `codecarto/routers/unified_parser_router.py` | `/parse/*` endpoints |
| `codecarto/services/unified_parser_service.py` | Directory walk + language dispatch |
| `codecarto/services/parsers/language_parser.py` | LanguageParser Protocol + ParserRegistry |
| `codecarto/services/parsers/python_language_parser.py` | Python adapter |
| `codecarto/services/parsers/c_language_parser.py` | C/H adapter |
| `codecarto/services/graph_serializer.py` | NetworkX -> gJGF, depth-aware sizing |
| `codecarto/services/github_service.py` | GitHub API client + `resolve_github_token()` / `create_headers()` |
| `codecarto/models/custom_layouts/compound_layout.py` | 4-pass hierarchical layout (dirs→files→symbols→sub-symbols, source-ordered) |
| `codecarto/services/position_service.py` | Layout registry; registers compound_layout |
| `web/src/features/graph/services/compound_layout.ts` | CompoundLayoutManager — bounding circles + `computeChildrenMap` (4-tier drag) |
| `web/src/layout/panel_registry.ts` | Dock panel registration table (id/config/mount) — add new panels here |
| `web/src/layout/layout_context.ts` | GL state hub — streaming, graphbase, GitHub auth status |
| `web/src/layout/panels/graphbase_panel.ts` | Graph Library panel (Snapshots / Saved / History / Recent) |
| `web/src/services/graphbase_service.ts` | `/db/*` client — bookmarks, snapshots, history |
| `graphbase/__init__.py` | Submodule public surface — `from graphbase import graphdb, get_db` |
| `graphbase/src/main.py` | MongoDB router (bookmarks / snapshots / history / graph CRUD) |
| `web/src/features/graph/services/graph_renderer.ts` | D3 renderer + radial menu + onViewSource (github.com/blob/#L) |
| `web/src/features/graph/services/renderers.ts` | Renderer registry |
| `docs/llm/EXTENDING.md` | How to add renderers, language parsers, endpoints |
