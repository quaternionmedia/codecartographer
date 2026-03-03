# Large Repository Parsing — Phased Roadmap

## Goal

One coherent, navigable graph of an entire codebase.
`torvalds/linux` is the gold standard: ~75K files, ~20M lines.

"Manageable" does not mean "all nodes at once."  It means a hierarchical graph
that starts at a high-level abstraction (directory tree, ~100–300 nodes even for
linux) and lets the user drill into areas of interest by expanding nodes.  The
same force-directed canvas grows progressively as the user explores.

```
torvalds/linux  depth=0  →  ~300 directory nodes  (completely manageable)
  Expand kernel/          →  150 sub-dirs appear
  Expand kernel/sched/    →  20 files appear
  Click fair.c            →  50+ function nodes appear
```

---

## Current State (Phase 1 — shipped)

### Parser coverage
All extensions below produce unified gJGF nodes with schema
`{depth, language, kind, label, file, line, meta}`.

| Parser | Extensions | Symbols |
|--------|-----------|---------|
| Python | `.py` | function, class, decorator, method |
| C/C++ (libclang) | `.c .h .cpp .cc .cxx .hpp .hxx` | function, class, struct, enum, typedef, macro |
| JavaScript | `.js .jsx .mjs` | function, class, arrow-const |
| TypeScript | `.ts .tsx` | + interface, type alias, enum, decorator |
| Rust | `.rs` | fn, struct, enum, trait, impl, mod, macro_rules, type alias |
| Go | `.go` | func (incl. method receivers), type struct, type interface |
| Java | `.java` | class, interface, enum, @interface |
| C# | `.cs` | class, interface, enum, struct, namespace |
| Kotlin | `.kt .kts` | fun, class/data class/object, interface, typealias |
| Swift | `.swift` | func, class, struct, protocol, enum |
| Ruby | `.rb` | def, class, module |
| PHP | `.php` | function, class, interface, trait |
| Scala | `.scala` | def, class/case class/object, trait, type alias |
| Shell | `.sh .bash` | function (both `name()` and `function name` styles) |

C/C++ requires the optional `[c-parsing]` extra (`uv pip install -e ".[c-parsing]"`).
All other parsers use zero extra dependencies (regex only).

### Interactive expansion (Phase 1 UX)
- **Depth 0**: directory tree only (~300 nodes for linux)
- **Depth 1**: files inside a directory expand on click
- **Depth 2**: symbols inside a file expand on click
- State: `parseDirectory` stored after each unified parse so expansion calls
  reuse the same directory context without re-submitting the form.

---

## Phase 2 — Interactive Node Expansion (planned, not yet implemented)

This is the core UX feature that makes the single-large-graph experience work.

### 2-A. D3 double-click to expand

**File**: `web/src/features/graph/services/graph_renderer.ts`

- Accept `onNodeExpand?: (nodeId: string, currentDepth: number) => void` via
  `GraphStylingOptions` index signature (`[key: string]: unknown`).
- In the node dblclick handler: if `node.depth < 2`, call `onNodeExpand(node.id, node.depth)`.
- Visual indicator: expandable nodes (depth 0/1 with no children yet rendered)
  draw with a dashed border (`stroke-dasharray`) to signal they can be expanded.

### 2-B. Graph merge action

**File**: `web/src/state/actions.ts`

Add `PlotActions.expandGraphNode(nodeId)`:
- Retrieve `parseDirectory` from state (set by `plotUnified`).
- Call `POST /parse/expand` with the node ID.
- Merge the returned `GraphData` into the existing graph:
  - Nodes: patch nodes win (replace by ID).
  - Edges: deduplicate by `source→target` key.
- Call `createGraphVnode()` to re-render without resetting the canvas.

### 2-C. Position-preserving re-render

**File**: `web/src/features/graph/services/graph_renderer.ts`

Keep a module-level `_positionCache: Map<string, {x: number, y: number}>`.
- On tick/end: write current node positions into the cache.
- On new render: restore `x, y` from cache; new nodes start near their
  parent's cached position if available.
- Restart simulation with `alpha(0.3)` (gentle settle) instead of `alpha(1)`.

### 2-D. Collapse support

Extend the right-click context menu in `graph_renderer.ts`:
- Add "Collapse subtree" option.
- BFS from the clicked node to find all reachable descendants.
- Remove descendant nodes and their edges from `graphData`.
- Re-render (positions of surviving nodes are already in cache).

---

## Phase 3 — Download-on-demand (medium effort)

**Problem**: GitHub API returns file metadata (name, url) but not content.
Currently content is fetched lazily per-file click.  For bulk parsing of a
subtree we need content without per-file API calls.

### 3-A. Batch download in parse request

Add `download_content: bool = False` to `UnifiedParseRequest`.

When enabled:
- Identify `RawFile` entries with empty `raw` but populated `url` (GitHub raw URL).
- Download all in parallel via `httpx.AsyncClient` (already a dependency).
- Guard with `max_file_downloads: int = 200` to prevent runaway requests.
- Sufficient for focused subtree parsing (one directory at a time).

**Files to modify**:
- `codecarto/services/unified_parser_service.py` — async download helper
- `codecarto/routers/unified_parser_router.py` — expose flag in request model

### 3-B. GitHub token support

Pass `Authorization: Bearer <token>` header in download requests to raise
API rate limit from 60 → 5 000 req/hour (unauthenticated vs authenticated).

---

## Phase 4 — Git Archive Endpoint (high impact)

**Problem**: GitHub API has rate limits and doesn't expose a bulk download.

### 4-A. New endpoint

`POST /parse/repo?url=<github>&depth=2&extensions=.c,.rs`

Steps:
1. `git archive --remote <url> HEAD | tar x` into a temp dir (single HTTP request, no API).
2. Walk local filesystem — zero rate limit concerns.
3. Dispatch all files to registered language parsers.
4. Stream gJGF back as chunked HTTP.

Enables complete parsing of `torvalds/linux` in one request (~1 GB download,
5–15 min parse depending on server hardware).

**Dependencies**: `git` CLI on PATH (standard on most servers).  No Python
package changes required.

### 4-B. Disk-backed parser cache

Hash `(repo_url, ref, extensions)` → cache key.  Store serialized gJGF on
disk.  Re-parse only when the ref (commit SHA) changes.  Subsequent loads of
the same repo are instant.

---

## Phase 5 — WebSocket Streaming (full solution)

**Problem**: Phase 4 parse of a large repo takes minutes; browser times out.

### 5-A. Background job model

- `POST /parse/job` → `{ job_id }` (immediate)
- Worker thread parses incrementally, broadcasting progress.
- `GET /parse/job/{id}/ws` → WebSocket streaming:
  - `{ type: "progress", pct: 42, message: "kernel/sched/ …" }`
  - `{ type: "chunk", data: <partial gJGF> }`
  - `{ type: "done" }`
- Frontend incrementally merges chunks (builds on Phase 2-B merge logic).
- User sees the graph grow in real-time as files are parsed.

**Files to create/modify**:
- `codecarto/routers/parse_job_router.py` — job endpoints + WebSocket
- `codecarto/services/parse_job_service.py` — thread pool + job registry
- `web/src/state/actions.ts` — `subscribeToParseJob()` using native `WebSocket`

### 5-B. Resumable jobs

Store job state in a lightweight DB (SQLite via `aiosqlite` or existing Motor).
Allow the browser to reconnect and continue receiving chunks after a disconnect.

---

## Phase 6 — Rendering at Scale (>5 K nodes)

Current SVG renderer degrades at ~1 K–5 K nodes due to O(n²) charge force and
DOM overhead.  Options in order of effort:

| Option | Effort | Max nodes | Notes |
|--------|--------|-----------|-------|
| **Barnes-Hut force** | Low | ~10 K | Replace ManyBody with quadtree approximation; `d3-force` has this built-in via `theta` parameter |
| **Canvas renderer** | Medium | ~50 K | Port SVG logic to `CanvasRenderingContext2D`; eliminates DOM overhead |
| **WebGL renderer** | High | 500 K+ | `three.js` or `pixi.js`; requires significant rewrite of interaction layer |
| **Server-side layout** | Medium | Unlimited | Compute positions on server (networkx `spring_layout`), send static `{x,y}`; no live physics needed for very large graphs |

For the linux use case at depth 0 (~300 nodes), the current SVG renderer is
already sufficient.  Canvas becomes relevant only if the user expands many
subtrees simultaneously.

### Recommended path

1. Enable Barnes-Hut in D3 (one-line change: `d3.forceManyBody().theta(0.9)`).
2. Add a "Pause physics" button so the simulation stops after initial settle,
   dropping CPU to zero for static exploration.
3. Implement Canvas renderer as a fourth renderer option when node count
   crosses a configurable threshold (default: 3 000 nodes).

---

## Quick Reference — Extension Points

| Phase | Key file(s) |
|-------|-------------|
| New language parser | `codecarto/services/parsers/` — implement `LanguageParser` protocol, import in `unified_parser_service.py` |
| Phase 2 expand UX | `web/src/features/graph/services/graph_renderer.ts`, `web/src/state/actions.ts` |
| Phase 3 download | `codecarto/services/unified_parser_service.py`, `codecarto/routers/unified_parser_router.py` |
| Phase 4 git archive | New `codecarto/routers/parse_job_router.py` + service |
| Phase 5 WebSocket | Extend parse job router + `web/src/state/actions.ts` |
| Phase 6 canvas | New renderer in `web/src/features/graph/services/`, registered in `renderers.ts` |
