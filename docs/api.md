# API Reference

REST API documentation for Codecarto backend.

**Base URL:** `http://127.0.0.1:<port>`, where the port is
`codecarto.cli.DEFAULT_PORT`; `uv run codecarto serve --help` prints it, and
`CODECARTO_PORT` or `--port` overrides it. The examples write `$API` for that
base.
**Interactive docs:** `$API/docs` lists every route in the running server's
OpenAPI schema. The schema has no WebSockets and leaves out `/app`, `/db/` and
the `/pam/api/*` aliases; each is named in its section below.
**Identity:** `$API/openapi.json` names the app `codecarto`.

---

## Overview

| Prefix | Tag | Description |
|--------|-----|-------------|
| `/parse` | parse | **Unified parse (all languages, recommended)** |
| `/plotter` | plotter | Demo data + Notebook-renderer HTML pre-render |
| `/c-parser` | c-parser | C/H semantic parsing (requires `[c-parsing]` optional dep) |
| `/repo` | repo | GitHub + local repository tree operations |
| `/pam` | pam | PAM auth log monitor |
| `/system` | system | Derived system diagrams, read from a local clone |
| `/palette` | palette | Color palette management |
| `/lexicon` | lexicon | Hand-authored language lexicons, the construct vocabulary and the chrestomathy |
| `/cargo` | cargo | A Cargo workspace and its last recorded build, as graph data -- read, never run |
| `/topology` | topology | The harness's flows, as graph data |
| `/capabilities` | capabilities | The governance corpus's capability registry, as graph data |
| `/overview` | overview | dossier's reading of the estate, as graph data |
| `/estate` | estate | Every seam above and whether each is there |
| `/show` | show | Every family and project the corpus names, as graph data |
| `/auth` | auth | Which GitHub credential source is active |
| `/db` | db | Graphbase, when `MONGODB_URI` is set |

`/app` serves the built web application from `web/dist` when a build is present.
While developing, the frontend's dev server proxies each prefix above to the
backend, so the app and its API share an origin as they do in production;
`API_PATHS` in `web/vite.config.js` is that list.

---

## Unified Parse Endpoints

These are the recommended endpoints. They work across all registered languages
(`GET /parse/languages` lists them: Python by its AST, C/C++ by libclang, Rust by
an item-level reader, linker scripts by theirs, the rest by a regex per language)
and produce gJGF output that any renderer can display.

Folder and file ids are the path from the root (`file::ws/crates/hal/src/lib.rs`),
so two files with one name are two nodes.

Every node whose language and kind `codecarto/data/constructs.yaml` maps also
carries `construct` -- what it *is*, the same across languages (`type.product`
for a C or Rust struct) -- and, where its qualifiers, attributes or body say so,
`meta.facets` (`memory.unsafe`, `firmware.interrupt`, `layout.section`), and, for
a construct with a look, `construct_color` and `construct_name` (what
[Color By](ui.md#graph-settings) draws for a construct, and the key names). A kind the vocabulary lists under
`not_constructs`, with its reason, carries none -- Python's calls, names and
literals are what a body does, not what it declares -- and neither do the
walk's own `directory` and `file` nodes. Every route that serializes a graph to
gJGF stamps these, the unified streams stamp each file's nodes as they parse,
and a cached graph is stamped again whenever `/parse/unified` or a stream serves
it, so any graph on the canvas can be read by `POST /lexicon/chrestomathy/census`.
A re-stamp applies the vocabulary as it is now to what the cache kept: a mapping
added since is applied, but a fact the parser had not recorded when the graph
was cached (C's `meta.automatic` on a local) is not recovered, and a construct
the vocabulary no longer gives is not taken back -- a change to what a parse
records bumps `GRAPH_SCHEMA_VERSION`, so the old graph is a miss. A local Rust
repository with a recorded `target/codecarto/check.jsonl` has rustc's
diagnostics on the items they name (`meta.diagnostics`, `meta.messages`,
`meta.diagnostics_recorded_at`), and `metadata.recorded_check` is that document's
row. A check older than a source or manifest is not used: nothing is placed from
it, and the row says `used: false`, `stale: true` and why. With a recorded
`target/codecarto/<bin>.map` the linker script's regions and sections carry
what the link measured (`meta.measured`) and functions and statics their size (`meta.bytes`). A map
older than anything the link reads -- a Rust, C, C++ or assembly source, a linker
script such as `memory.x`, a manifest, `Cargo.lock` or `.cargo/config.toml`, but
not a README or other docs -- is not used: the regions it would measure say so
(`meta.measured.used: false`) and nothing carries its figures. `/cargo` judges
the same map by the same rule (`link_map_service.link_input`).

### POST `/parse/unified`

Parse a directory tree to the requested depth and return a gJGF graph.

**Request Body:**
```json
{
  "directory": {
    "info": { "owner": "user", "name": "myrepo", "url": "..." },
    "size": 12345,
    "root": {
      "name": "myrepo",
      "files": [{ "name": "main.py", "size": 1234, "raw": "..." }],
      "folders": []
    },
    "is_partial": false
  },
  "depth": 2,
  "extensions": [".py", ".c"],
  "layout": "spring_layout",
  "annotate_lexicon": false
}
```

**`annotate_lexicon`** (default `false`): stamp Lexicon abstraction-layer
data (`layer_ordinal`, `meta.lexicon_layers`) onto nodes whose language
has one (`c`, `python` and `rust`; `GET /lexicon/` lists them — see
`docs/architecture.md`, *Lexicons and the construct vocabulary*). Requests
with this set to `true` bypass the response cache, whose key does not include
it.

**`layout` values:**

| value | description |
|-------|-------------|
| `spring_layout` | Force-directed (default) |
| `compound_layout` | Hierarchical: dirs → files → symbols in nested orbits |
| `circular_layout` | Nodes on a circle |
| `kamada_kawai_layout` | Energy-minimized spring |
| `spectral_layout` | Graph Laplacian eigenvectors |

**depth values:**
| depth | output |
|-------|--------|
| 0 | directories only |
| 1 | directories + files |
| 2 | + top-level symbols (class, function, struct, …) |
| 3 | + sub-symbols (arguments, fields, enum constants, a C function's locals) |

**Response:**
```json
{
  "status": 200,
  "message": "parse/unified - Success",
  "results": {
    "graph": {
      "nodes": {
        "dir::myrepo": { "metadata": { "depth": 0, "kind": "directory", "label": "myrepo", "language": "unknown" }},
        "file::myrepo/main.py": { "metadata": { "depth": 1, "kind": "file", "label": "main.py", "language": "python" }},
        "main.MyClass": { "metadata": { "depth": 2, "kind": "class", "label": "MyClass", "language": "python", "line": 5 }}
      },
      "edges": [
        { "source": "dir::myrepo", "target": "file::myrepo/main.py", "metadata": { "kind": "contains" }},
        { "source": "file::myrepo/main.py", "target": "main.MyClass", "metadata": { "kind": "contains" }}
      ],
      "directed": true
    },
    "metadata": {
      "layout": "Spring",
      "type": "d3",
      "nodeCount": 3,
      "edgeCount": 2,
      "palette_id": "0"
    }
  }
}
```

A parser that could not run over files the graph still draws -- C without
libclang -- says so in `metadata.notes`, one sentence per batch
(`"2 c file(s) drawn without their contents: libclang is not installed, …"`).
A result with notes is not cached, on this route or either stream: a replay
carries nodes and edges and nothing beside them, so it would arrive empty and
silent. The next request parses again.

---

### POST `/parse/stream`

Same as `/parse/unified` but streamed as [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
instead of one blocking JSON response. Use this for any repo big enough that
the user would otherwise stare at a blank screen — nodes render as they
arrive instead of all at once at the end.

**Request Body:** same as `/parse/unified`.

**Response:** `Content-Type: text/event-stream`. Each event is
`event: <type>\ndata: <json>\n\n`:

| event | payload | when |
|-------|---------|------|
| `meta` | `{nodeCount, edgeCount, layout, from_cache?}` | first, once the graph size is known |
| `note` | `{message}` | after `meta`, once per batch a parser could not read (`metadata.notes` above) |
| `node` | flat node dict (`id` + unified schema fields) | once per node |
| `edge` | `{source, target, label?, ...}` | once per edge, after all nodes |
| `done` | `{elapsed_ms, from_cache?}` | last |
| `error` | `{message}` | on exception, in place of `done` |

If the request matches a cached graph, all events are replayed instantly
from the cache (`from_cache: true`) instead of re-parsing.

After a fresh stream completes (the `done` event is emitted), the full
accumulated graph is automatically written to cache — subsequent requests
with the same URL, mode, layout, and extensions, under the same graph schema
version, are served as instant replays without re-parsing. A stream that
carried a `note` is not written: its replay would arrive without it.

---

### POST `/parse/stream-url`

Two-phase variant of `/parse/stream` that fetches a GitHub repo *and*
streams its parse — no separate `/repo/tree` round-trip first.

**Request Body:**
```json
{ "url": "https://github.com/owner/repo", "depth": 2, "layout": "Spring" }
```

**Response:** Same SSE event types as `/parse/stream`, plus a `fetching`
event (`{message}`) emitted during phase 1 (repo tree fetch) before any
`node`/`edge` events arrive. Phase 2 (symbol parsing) streams nodes as each
file's content is fetched and parsed, and a `note` where a batch could not be.

After streaming completes, the full accumulated graph is written to cache
(GitHub URLs only, and not when the stream carried a `note`) — the next
request for the same repo and settings is an instant cache replay.

---

### POST `/parse/expand`

Expand a single file node to reveal its symbols (depth-2/3 nodes).
Useful for lazy-loading symbol details after an initial depth-1 parse.

**Request Body:**
```json
{
  "directory": { "...same as /parse/unified..." },
  "node_id": "file::src/main.py",
  "depth": 2
}
```

**Response:** Same shape as `/parse/unified` but contains only the sub-graph
rooted at `node_id` and its descendants.

---

### GET `/parse/languages`

List all registered language parsers and their file extensions: one key per
language, each with the extensions it reads.

**Response** (the first four of the languages):
```json
{
  "status": 200,
  "message": "parse/languages - Success",
  "results": {
    "languages": {
      "python": [".py"],
      "c": [".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
      "rust": [".rs"],
      "linker": [".ld", ".lds", ".x"],
      ...
    }
  }
}
```

---

## Plotter Endpoints

Two demo and rendering routes. To parse, use `/parse/unified`.

### POST `/plotter/demo`

Generate a demo graph from the codecarto source code itself: the `.py` files of
this repository's `codecarto/` package, read through
`UnifiedParserService.parse` as every other parse is read. `parse_by` sets only
the depth (`plotter_router.py`, `_DEMO_MODE_TO_DEPTH`):

| `parse_by` | `depth` | output |
|------------|---------|--------|
| `directory` | 1 | directories and files |
| anything else (`ast`, `dependencies`, the default `code`) | 2 | + symbols and file-to-file dependency edges |

**Request Body:**
```json
{
  "options": { "palette_id": "0", "layout": "Spring", "type": "d3", "parse_by": "ast" }
}
```

---

### POST `/plotter/render/html`

Convert GraphData JSON to pre-rendered HTML for the Notebook renderer.

**Request Body:**
```json
{
  "graph_data": { "graph": {...}, "metadata": {...} },
  "options": { "layout": "Spring" }
}
```

**Response:**
```json
{
  "status": 200,
  "message": "Success",
  "results": { "text/html": "<html>...</html>" }
}
```

---

## C Parser Endpoints

Require the optional `c-parsing` extra (libclang), which the install in
[Getting Started](getting-started.md) includes.

### POST `/c-parser/file`

Parse a single C/H source file.

**Request Body:**
```json
{ "path": "/absolute/path/to/file.c" }
```

**Response:**
```json
{
  "status": 200,
  "message": "c-parser/file - Success",
  "results": {
    "graph": {
      "nodes": [...],
      "edges": [...],
      "meta": {
        "files": ["file"],
        "node_count": 12,
        "edge_count": 8,
        "kind_counts": { "function": 3 },
        "edge_kinds": { "CALLS": 5, "FIELD_OF": 2, "POINTS_TO": 1 },
        "diagnostics": {
          "missing_header": 0,
          "unknown_type": 0,
          "other": 0,
          "files_with_warnings": 0,
          "worst_files": []
        },
        "skipped_files": []
      }
    }
  }
}
```

> **Note:** `/c-parser/*` returns a flat `{nodes, edges, meta}` dict, not
> gJGF, and the web application does not call it. `/parse/unified` with
> `.c`/`.h` extensions produces gJGF natively, with the *same* cross-file
> CALLS resolution, stub-header diagnostics, and
> `has_parse_warning` flagging as this dedicated pipeline — both call into the
> same `CParser` engine (per-symbol extras like `field_count`/`qualifiers`
> live under each unified node's `meta` field instead of top-level). Prefer
> `/parse/unified` unless you need this flat shape.

When parsing without a `compile_commands.json` (i.e. `parse_files`/`parse_directory`,
which backs `/c-parser/file`, `/c-parser/directory`, and `/c-parser/github`), each
file is parsed standalone against a bundled set of stub POSIX headers
(`codecarto/data/c_stubs/`) rather than the project's real build setup — see
`codecarto/services/parsers/c_parser.py`. `meta.diagnostics` reports how often that
fell short (missing headers, unknown types), and `meta.skipped_files` lists
source files skipped because they target a single non-default platform (e.g.
`compat/apple-*.c`, `compat/mingw.c`). Nodes whose source file produced parser
errors are flagged `has_parse_warning: true` and rendered with a dashed amber
border in the graph view.

---

### POST `/c-parser/directory`

Parse all C/H files in a directory.

**Request Body:**
```json
{
  "path": "/absolute/path/to/dir",
  "compile_commands": null,
  "subsystem": null,
  "max_files": 200
}
```

---

### POST `/c-parser/github`

Download a GitHub repository and parse all C/H files. Blocking — the
response isn't sent until every file is parsed. For large repos, prefer
`/c-parser/stream-github` below for direct API usage when you want
file-by-file progress events.

**Request Body:**
```json
{ "url": "https://github.com/owner/repo", "max_files": 200 }
```

---

### POST `/c-parser/stream-github`

Streamed variant of `/c-parser/github`. The web application's C examples go
through `/parse/stream-url`; this route is for direct callers. libclang parsing
is synchronous CPU-bound work, so it runs in a background thread while this
endpoint drains its progress queue and forwards SSE events as they arrive —
see `docs/architecture.md`, *C: two pipelines*.

**Request Body:** same as `/c-parser/github`.

**Response:** `Content-Type: text/event-stream`:

If the request matches a cached parsed graph (`CacheService`, Cache A — see
`docs/architecture.md`, *The two caches*), all events are replayed
instantly (`from_cache: true`) with positions baked into each node and a
`reposition` event restoring the saved layout.

| event | payload | when |
|-------|---------|------|
| `fetching` | `{message}` | during archive download/extract (skipped on cache hit) |
| `meta` | `{fileCount, skippedCount, from_cache?}` | once the target file list is known, before parsing starts |
| `node` | flat node dict + `language: "c"`, `depth: 2`, `x`, `y` | streamed file-by-file as libclang finishes each one |
| `reposition` | `{nodeId: {x, y}, …}` | after all nodes — corrects placeholder positions to the final layout |
| `edge` | `{source, target, label, weight}` | **all at once, after `reposition`** — see below |
| `done` | `{elapsed_ms, node_count, edge_count, diagnostics, skipped_files, from_cache?}` | last |
| `error` | `{message}` | on exception, in place of `done` |

After streaming completes, the parsed graph (with final positions) is
written to `CacheService` (Cache A) — the next request for the same URL
and layout is served as an instant cache replay.

**Why nodes stream but edges arrive in one batch:** declarations (pass 1)
are parsed and emitted one file at a time, so nodes appear as libclang
works through the file list. Call edges and derived type edges
(FIELD_OF/POINTS_TO) need the *complete* cross-file node set to resolve
their targets, so they can only be computed — and streamed — after every
file's declarations are in.

### GET `/c-parser/visualizer?path=<optional>`

Serve the C Semantic Visualizer HTML page. Without `path`, shows a
built-in demo graph (`linux/mm/`); with `path`, parses the given
filesystem path with libclang and injects the result in place of the
demo graph.

---

### GET `/c-parser/cache`

List extracted GitHub repos in the C-parser's repo cache (newest first).
This is a *different* cache from `GET /parse/cache` — that one lists cached
*parsed graphs*; this one lists cached *extracted source trees* (downloaded
zip contents, re-parsed fresh on every request — only the download+extract
step is skipped on a hit). `docs/architecture.md`, *The two caches*, sets
the two side by side.

**Response:**
```json
{
  "status": 200,
  "message": "c-parser/cache - Success",
  "results": {
    "entries": [
      { "key": "git-git", "owner": "git", "repo": "git", "url": "...", "ts": 1234567890.0, "age_seconds": 120, "size_bytes": 45000000 }
    ]
  }
}
```

---

### DELETE `/c-parser/cache/{key}`

Evict a cached extracted repo by its `{owner}-{repo}` key (from the `key`
field in `GET /c-parser/cache`'s entries). Counterpart to
`DELETE /parse/cache/{key}`.

```bash
curl -X DELETE "$API/c-parser/cache/git-git"
```

---

## Repository Endpoints

Handle both GitHub URLs and local filesystem paths — `url` is checked
against `'github.com' in url` (see `github_service.is_github_url`) to decide
which backend (`github_service.py` vs `local_repo_service.py`) handles the
request. There is no separate set of local-only endpoints.

### GET `/repo/tree`

Fetch the directory tree of a GitHub repository **or** a local path.

For GitHub URLs, the result is cached (see `docs/architecture.md`, *The two
caches*, for the layout) — a repeat call for the same repo
within `CC_CACHE_TTL` (default 24h) returns instantly with no GitHub calls.
On a cache miss, the repo's full tree is fetched in two GitHub API calls
(`github_service.fetch_tree_fast`, the Git Trees API) regardless of repo
size, then file content is fetched per the repo's size tier: full content
for repos under `_CONTENT_FETCH_LIMIT_KB` (~5MB), structure only for repos
under `_STRUCTURE_FETCH_LIMIT_KB` (~50MB), and a shallow single-level
listing (`is_partial: true`) for anything larger or if GitHub truncates the
recursive tree response.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | GitHub repository URL, or a local filesystem path |

**Example:**
```bash
curl "$API/repo/tree?url=https://github.com/fastapi/fastapi"
curl "$API/repo/tree?url=/path/to/local/project"
```

**Response:**
```json
{
  "status": 200,
  "message": "read_github_url - Success",
  "results": {
    "info": { "owner": "fastapi", "name": "fastapi", "url": "..." },
    "size": 1234567,
    "root": { "name": "fastapi", "files": [...], "folders": [...] },
    "is_partial": false
  }
}
```

**Notes:**
- GitHub: no repository is refused for its size; one of 50 MB or more gets the
  shallow listing above. A private repository needs a token, resolved in the
  order `docs/services.md` gives under *GitHub Token* (`gh auth login` is
  enough on a workstation)
- Local: default extension filter is every extension `ParserRegistry`
  knows about (not just `.py`); default excludes `.git`, `.venv`,
  `node_modules`, `.vs`, `.idea`, `bin`, `obj`, etc. (see
  `local_repo_service.get_local_repo`)

---

### GET `/repo/subtree`

Lazily expand a single folder path within a previously fetched repository
(GitHub or local).

**Query Parameters:** `url`, `path`

If the repo's full source tree was already cached (e.g. after a `/repo/tree`
call) and the tree is non-partial (`is_partial: false`), the subfolder is
served directly from the cache without an additional GitHub API call.

---

### GET `/repo/expand-all`

Expand all folders in a partial GitHub repo tree to `max_depth` (default 3),
returning a `Directory`. It is `is_partial: true` when any folder in it was
left unlisted -- one below `max_depth`, or one GitHub refused to list -- and
each such folder is an empty `Folder`, which the Files panel then draws with
`…` to read on click. A refused root is an error, not an empty tree.

**Query Parameters:** `url`, `max_depth` (optional, default 3)

If the full tree is already cached the response is served immediately with no
GitHub calls. The result is a `Directory` model in the same shape as
`/repo/tree`.

---

### GET `/repo/examples`

The examples bundled with this checkout (`examples/` at the repository root),
for the project selector to offer beside its GitHub ones: each with `id`,
`label`, `language`, `title`, the absolute `path` it is read from, and `cargo`
-- whether it is a Cargo workspace, whose recorded documents the selector also
loads into the Cargo panel. Only what `codecarto/services/examples_service.py`
names is offered, and an installed package, which has no `examples/`, answers
an empty list.

---

## PAM Monitor Endpoints

### GET `/pam/ui`

Serve the PAM auth log monitor HTML frontend (URL-patched for current server).
The page calls `/pam/api/status`, `/pam/api/history`, `/pam/api/sessions` and
`/pam/api/sessions/{session_id}`, which answer as the four routes below and
are kept out of the schema.

### GET `/pam/status`

Check PAM monitor status (running, log source, event count).

### GET `/pam/history?minutes=30`

Parsed PAM events from recent log history (`minutes`: 1-1440, default 30).

### GET `/pam/sessions`

List captured authentication sessions.

### GET `/pam/sessions/{session_id}`

All events for a specific captured session.

### WebSocket `/pam/ws/live`

Stream real-time PAM events as JSON objects:
```json
{ "timestamp": "...", "user": "alice", "event_type": "accepted", "rhost": "192.168.1.10" }
```

### WebSocket `/pam/ws/replay?session_id=<id>`

Replay a captured session's events at 3x speed.

---

---

## Derived System Endpoints

A diagram derived from a repository's own declarations by
`codecarto/services/system_composer.py`, rather than drawn by hand. The
repository is named, and found beside this checkout by that name; a name with a
path separator or a leading dot is refused.

### GET `/system/repos`

The repositories this server can find beside its checkout, and where each is.

### GET `/system/compose?repo=moat`

The components and edges the named repository declares.

### GET `/system/events?repo=moat&limit=30`

Recent changes and in-flight branches in the named repository (`limit`: 1-200,
default 30).

### WebSocket `/system/ws/replay?repo=moat`

The same changes replayed at a readable pace. Every frame carries
`"replay": true`; it is the clone's history, not a live feed.

---

## Auth Endpoints

### GET `/auth/github`

Report the active GitHub credential source and whether the backend has a
valid token. Useful for diagnosing the `GITHUB_TOKEN`-vs-keyring shadowing
issue described in *GitHub token resolution order* (`governance/qm/adr/`).

**Response:**
```json
{
  "source": "gh CLI keyring",
  "authenticated": true,
  "token_prefix": "gho_XXXX…"
}
```

`source` is one of: `"CC_GITHUB_TOKEN env var"`, `"gh CLI keyring"`,
`"GITHUB_TOKEN/GH_TOKEN env var"`, `"Docker secret"`, or
`"none (unauthenticated)"`.

---

## Graphbase Endpoints (`/db/*`)

Mounted only when `MONGODB_URI` is set. Without it, `GET /db/` returns
`{"available": false, "reason": …}` and every other `/db/*` route returns 404.
See `governance/qm/adr/DRAFT-cache-service-vs-graphbase.md` for why this store
is separate from the filesystem `CacheService`.

The graphbase submodule exposes four collections:

| Collection | Purpose | Key |
|------------|---------|-----|
| `graph` | Named NetworkX graphs (legacy nx.node_link_data format) | `name` |
| `snapshots` | Full rendered graph snapshots (gJGF nodes + edges, instant replay) | `name` |
| `bookmarks` | Lightweight URL + parse-settings records (re-streams on load) | `name` |
| `history` | Per-URL render history, capped at 20 entries per URL | `(url_hash, captured_at)` |

### Bookmarks

#### POST `/db/bookmarks?name=&url=&layout=&depth=&extensions=`
Save or overwrite a named source bookmark. Returns `{"message":"Bookmark saved","name":"..."}`.

#### GET `/db/bookmarks`
List all saved bookmarks. Returns an array of `{name, url, layout, depth, extensions, saved_at}` objects.

#### DELETE `/db/bookmarks/{name}`
Delete a named bookmark. Returns 404 if not found.

### Graphs

Named NetworkX graphs, in `nx.node_link_data` form (`graph` collection);
`nx.node_link_graph(result)` rebuilds one.

#### POST `/db/graph/insert?name=`
Body: the graph's node-link data. Stores it under `name`.

#### POST `/db/graph/{name}`
An empty graph under `name`.

#### GET `/db/graph/{name}`
The graph's node-link data.

#### GET `/db/graphs`
Every stored graph's name.

#### POST `/db/graph/{name}/node?node_id=` · DELETE `/db/graph/{name}/node?node_id=`
Add or remove a node.

#### POST `/db/graph/{name}/edge?source=&target=` · DELETE `/db/graph/{name}/edge?source=&target=`
Add or remove an edge.

#### DELETE `/db/graph/{name}`
Removes the graph.

### Snapshots

#### POST `/db/snapshots?name=`
Body: `{nodes, edges, meta}` in gJGF-adjacent format. Upserts a named graph
snapshot for instant replay — no re-streaming required. Computed fields
(`name`, `saved_at`) cannot be overridden by body content.

#### GET `/db/snapshots`
List snapshot metadata (excludes the full nodes/edges payloads).

#### GET `/db/snapshots/{name}`
Retrieve a full snapshot including nodes and edges.

#### DELETE `/db/snapshots/{name}`
Delete a named snapshot.

### History

#### POST `/db/history?url=`
Body: `{nodes, edges, meta}`. Append a render snapshot for the given URL.
The backend assigns `url_hash` (SHA-256(url)[:16]) and `captured_at` (unix
timestamp). Entries are capped at 20 per URL; oldest are pruned automatically.
Computed fields cannot be overridden by body content.

#### GET `/db/history/{url_hash}`
List history metadata for a URL hash (no node/edge payloads).

#### GET `/db/history/{url_hash}/{captured_at}`
Retrieve a specific history entry (full data).

#### DELETE `/db/history/{url_hash}/{captured_at}`
Delete a specific history entry.

---

## Lexicon Endpoints

Hand-authored per-language ontologies (reserved words/operators on a
hierarchy of abstraction layers), projected into the same graph pipeline
the parsers use. `docs/architecture.md`, *Lexicons and the construct
vocabulary*, describes them.

### GET `/lexicon/`

List available language ids (`results.languages`, e.g. `["c", "python", "rust"]`).

### GET `/lexicon/{language}`

Full validated lexicon as JSON (layers, groups, tokens).

### GET `/lexicon/{language}/graph`

gJGF graph (`{graph: {nodes, edges}, metadata}`) — the same shape and
serialization pipeline (`GraphSerializer.serialize_to_gjgf`, real layout
positions included) every parsed-code graph uses, so it renders through
the existing D3 pipeline unchanged. Every node carries `language`,
`layer_ordinal` and `kind`; every node on a layer (layer, group, token) also
carries `layer_color`, which the `colorBy: 'layer'` styling option paints, and
`meta.lexicon_layers`, from which the legend names the layer — what an
annotated parsed node carries. Use this route, not `LexiconService.to_json()`; the front end cannot draw
the node-link shape.

### GET `/lexicon/{language}/index`

Token-spelling → contexts lookup (which layers/groups a token appears
in) — the join `unified_parser_service.py`'s `annotate_lexicon` flag
uses to enrich real parsed graphs (see `POST /parse/unified` above).
Annotated nodes also carry `layer_color`, which
[Color By](ui.md#graph-settings) draws for an abstraction layer, and the legend names.

### GET `/lexicon/constructs`

The construct vocabulary (`codecarto/data/constructs.yaml`) as an index: each
construct's `id`, `name`, `gloss`, whether it is a `facet` (something a node can
*also* be) and the `languages` that spell or parse it. Registered before
`/lexicon/{language}`, which would otherwise answer for it.

### GET `/lexicon/chrestomathy/{construct}`

One construct set beside itself across every language: per language, the
`tokens` that spell it with their lexicon `contexts` (layer and group), the
parser `kinds` that realise it, what `carried_by` a facet in source (`#[interrupt]`,
`qualifier volatile`), and a `note`. **Every language the vocabulary lists under
`languages:` is a row of every construct, never a missing one**: a language with
no spelling has its note -- Rust has no `volatile`, C has no method -- and one the
vocabulary records nothing for has a note saying so. C, Rust, Python, assembly and
the linker script are listed, so each is a row of every construct. The crate
graph's nodes (`language: cargo`) are mapped under `graphs:`, which places them
without making Cargo a row: nothing is written in it. An unknown construct
is a 200 with `unreadable`, `problem` and the known ids as `remedy`.

### POST `/lexicon/chrestomathy/census`

The chrestomathy of a graph. Body: `{"nodes": [{"id", "language", "kind",
"construct"?, "meta"?: {"facets"?}}]}` -- the nodes on the canvas. Answers the
`constructs` and `facets` present, each with its `name`, `gloss`, `look`,
`count`, the `languages` it occurs in with their counts, and the `ids` of the
nodes that are it; then what was not placed, each as what it is: `walk` (the
walk's own `directory` and `file` nodes, whatever language a file carries),
`not_constructs` (a kind the vocabulary lists as no construct, with its
`reason`), `unplaced` (a kind of a listed language, or of a graph under
`graphs:`, the vocabulary neither maps nor lists), `outside`
(a language it lists in neither), `unknown` (a stamp naming a construct or facet
the vocabulary does not hold, with the `ids` that carry it -- a graph drawn
under another vocabulary) and `unlabelled` (no language at all), with the
`caveat`. A node that arrived without a stamp is stamped by the same rule as a
drawn graph; nothing sent is changed.

### GET `/lexicon/chrestomathy/{construct}/gjgf?layout=`

The same reading as `GraphData`: the construct at the centre, each language
around it (a silent one on a dashed edge, its note as the hover), each token on
the layer of the sense that spells this construct (Rust's `for` is iteration
under a loop, behaviour under an implementation), coloured by that layer's
`layer_ordinal` and naming it in `meta.lexicon_layers`. **An ordinal is a rank
within one language's lexicon, not a scale the languages share**: Rust's keyword
layers follow C's from 0 to 3 and its operator layers C's from 0 to 4, but
compile-time reasoning is C's keyword layer 4 and Rust's 5, and control flow is
Python's 0 and C's 3 -- one colour in two languages is one rank, and the layer's
name says what it is. `metadata.kind` is `chrestomathy`, with the `layers` ramp
and the `caveat`.

---

## Cargo Endpoints (`/cargo`)

A Cargo workspace's crates, targets, dependencies, features, native libraries
and device targets, and what the last recorded build said. **The window never
runs cargo**: running it on a path runs that path's build scripts, proc macros
and configured `rustc`. It reads manifests (`Cargo.toml`, `Cargo.lock`,
`.cargo/config.toml`, memory maps) and the two documents
`uv run codecarto cargo record <path>` writes under the workspace's `target/codecarto/`:
`metadata.json` (`cargo metadata --format-version 1`) and `check.jsonl`
(`cargo check --message-format=json`). The same envelope and absence rules as the
estate routes below: status 200, and a path that is not a workspace is
`unreadable` with a `problem`, a `remedy` and `where`.

### GET `/cargo/gjgf?path=&layout=&palette_id=&features=&transitive=`

The workspace as `GraphData`. Nodes: the workspace, each member crate with its
targets (lib, bin, build script, proc macro, tests), external crates, native
libraries (`links`, and `cargo:rustc-link-lib` from a recorded build script),
device targets from `.cargo/config.toml` (a `runner` is shown, never run) and
memory maps. A dependency edge is labelled and coloured by its kind; a
dev-dependency, an optional one and a platform-specific one are dashed and say
their condition. `features=true` adds features and what each enables;
`transitive=true` adds dependencies of dependencies -- cargo's resolution's
(edges labelled `resolved`) when `metadata.json` answered, the lockfile's
(`locked`) otherwise. Targets carry the recorded diagnostics in their label and
`meta.diagnostics`, from a `check.jsonl` newer than every source and manifest;
an older one is not used -- no diagnostic, build-script fact or outcome is drawn
from it -- and its row and the caveat say why. A binary with a recorded link map carries each region's fill in its label and
`meta.memory`, while the map is newer than everything the link reads -- every
source, linker script and manifest, by the rule the code map judges it by, and no
README or other docs.

`metadata` carries `kind: "cargo"`, `engine` (`cargo metadata` when a recorded
`metadata.json` is newer than every manifest, `manifests` otherwise -- a stale
document is not used, and says so), `generated_at`, every `documents` row with
`present`, `used`, `stale` and `problem` -- a recorded `<bin>.map` among them --
the recorded `diagnostics` counts, `build_success`, `firmware`, and the `caveat`.

### GET `/cargo/data?path=`

The reading without a layout: `packages` (with `dependencies`, `targets`,
`features`, `resolved_features`, `no_std`, `links`, `memory_maps`), `documents`,
`diagnostics`, `artifacts`, `scripts`, `build_success`, `firmware`, `memory`
(each recorded map's region use, by binary), `notes` and `caveat` -- comparable
with what `cargo metadata` says rather than only drawable.


---

## Show Endpoints

### GET `/show/subjects`

What the show seam can draw, read from the corpus's `families.json`, roster,
inventory, interop registry and palette: `families` (each with `name`,
`drives`, `within`, `subfamilies`, `members`, `all_members` and its `hue`),
`projects` (each public repository a family or the roster names, with its
`families`, `governed` -- `null` when git could not say, or when the corpus
checkout has no `project/codecartographer` branch and so holds too few project
branches to say, as a shallow or single-branch checkout does -- `phase`,
`description` and `views`), `unstated` and `private` (counted, never named),
`provenance` (the families document's path, the corpus `commit`, its `schema`,
and whether `CODECARTO_CORPUS` replaced the pin) and `notes` for any input it
could not read.

### GET `/show/index/gjgf?layout=&palette_id=`

Every family at once as `GraphData`: each family a node at its nesting depth,
each member inside the one family that claims it, and a member two families
claim drawn once, outside both outlines, with a `member_of` edge to each. Every
edge carries `basis` -- `claim` (the families document), `declared` (the
interop registry, labelled with the surface's protocol) or `measured` (a
member's manifests at its default branch name another estate repository by its
host URL; drawn dashed, and never used to place a member). `metadata.kind` is
`"show"`; `metadata.undeclared` lists measured links no surface declares, and
`metadata.unread` the members with no clone to measure.

### GET `/show/family/{name}/gjgf?layout=&palette_id=`

One family as `GraphData`: its subfamilies one level down, its members inside
it, a member it shares marked `also_in` with a `member_of` edge to a marker for
the other family, and every seam touching a member. A family the corpus does not
declare answers `unreadable` with the ones it does.

### GET `/show/project/{name}/gjgf?layout=&palette_id=`

One repository's place in the estate: its families, its `phase` and `attention`
claims beside its measured `recency`, its records on `project/<name>` with each
one's status, its capabilities, and the surfaces it sits on. A private member,
or a name no family or roster entry gives, answers `unreadable`.

### GET `/show/project/{name}/views`

Which of the project's three views can be drawn here: `estate` (the graph
above), `code` (the parse of its default branch on the host, with the `url` and
`depth` the Show panel streams through `/parse/stream-url`) and `system` (the
derived system monitor, available when a clone beside this one declares
components). A view that cannot be drawn carries `available: false`, a
`problem` and a `remedy`.

The corpus is read from `CODECARTO_CORPUS` when it is set, else the
`governance/qm` submodule. A families document that is missing, or at a schema
this window does not draw, answers `unreadable` rather than an empty estate.

At `layout=Compound`, the layout the Show panel opens in, the three drawing
routes re-place their nodes after the layout runs
(`codecarto/services/show_layout.py`). Each group is a ring around its own
node, spaced for its members' names. A subgroup is one item on its parent's
ring. The top level is packed in rows wider than they are tall. A node no
outline holds is placed between what it is joined to and pushed outside every
outline. A project's view is a ring around the project. Each ring member
carries `label_at` (`right`, `left`, `above` or `below`), the side its name goes
on. A group's own node carries `none`, because its outline names it. Any other
layout is left as it draws.

## Estate Endpoints

These routes draw data other projects produce, and `/estate/seams` says
whether each source is there. The drawing routes return `{graph, metadata}`.
When the source is missing they still return 200, with `results.unreachable`
or `results.unreadable`, plus `problem`, `remedy` and `where`. The front end's
`web/src/features/estate/seam_client.ts` tells the outcomes apart.

### GET `/estate/seams`

Every seam this window reads, probed once, as rows: `name`, `role`, `ok`,
`where`, `schema`, `detail`, `problem`, `remedy`, `routes`, `panel`. `ok` means
the far side answered with the shape this window expects — the harness's
encoding document, the registry file's `capabilities` list — not that a port
answered; *something answered and it was not the harness* is its own `problem`.
`live` counts the identified rows and `caveat` is the sentence to read first.
Always 200: an estate with nothing up is not a fault in the window looking at it.

### GET `/topology/gjgf?kind=&subject=&level=&layout=&palette_id=`

One of the harness's topologies as `GraphData` — `{graph, metadata}` — laid out
by any registered layout. `kind` names a shape (`GET /topology/available` lists
them); `subject` instead asks what the thread archive says about one project,
which the harness serves on loopback only. `metadata` carries `kind:
"topology"`, `caveat`, `measured`, `unmeasured`, `source` and `surveyed`: an
edge whose weight nobody measured is drawn dashed, never thin, and the caveat
says how much of the picture that is.

### GET `/topology/available`

What the harness offers and what this server can lay it out with:
`topologies` (each with `topology`, `caption`, `status`, `boxes`, `arrows`),
the harness's `encoding` (which channel carries which axis), and `layouts`. When
the harness is not answering, `topologies` is empty and the envelope carries the
`unreachable` sentence with the command that starts it.

### GET `/topology/data?kind=&subject=&level=`

What this window drew, edge by edge — widths, styles, whether each was measured
— so two windows onto one topology can be compared with each other rather than
only with the payload both were handed.

### GET `/capabilities/gjgf?layout=&palette_id=`

The capability registry (`governance/qm/ci/capability-registry.yaml`) as
`GraphData`. Every edge is one the registry declared — a capability claims one
rung, lives in one repository, and points at evidence per rung — and nothing is
added to make the picture connected. A rung with no evidence draws nothing; the
count of those is `metadata.unmeasured`. `metadata.kind` is `"capabilities"`.

### GET `/capabilities/data`

Every declaration with its rungs and pointers, without a layout: `rungs`,
`capabilities` (each with `id`, `title`, `repo`, `phase`, `stated_by`,
`stated_on`, `what`, `cannot_see`, `evidence`), `unmeasured`, `caveat`. A pin
that predates the registry answers `unreadable` with the propagation that moves
it.

### GET `/overview/gjgf?seam=&layout=&palette_id=`

dossier's overview seam (`dossier overview --json`) as `GraphData`. The one
relation drawn is that a section lists a subject; the masthead figures ride in
`metadata.masthead`, and `metadata.generated_at` / `metadata.written_at` say
when the reading was made. Every name is whatever the producer published —
redaction is inherited, never repeated. `metadata.kind` is `"overview"`.

**Any estate route, given a layout nobody registered**, answers 200 with
`unreadable`, the registry's own message and the registered names. Spellings
are normalised once (`Kamada Kawai`, `Kamada_Kawai`, `kamada_kawai_layout` are
one layout) and the result does not depend on which was sent. The seam is read
from `seam`, else `DOSSIER_OVERVIEW_SEAM`, else `overview.json` in the working
directory; a seam whose `schema` this window does not know is declined rather
than guessed.

### GET `/overview/data?seam=`

The sections themselves: `scope`, `generated_from` (how far back the sync
reached), `generated_at` (when the producer took the picture, when the seam
carries it), `written_at` (when the seam file was written -- a fact about the
file, shown when the producer's stamp is absent), `masthead` (each figure with
the producer's `label`, `value` and `note`), `sections` (each with `title` and
`rows`), `caveat`. The same reading the terminal prints as tables, so the two
windows can be compared.

---

## Palette Endpoints

### GET `/palette/default`

Get the built-in default palette. Response `results` is a `Palette`
object: `{id, bases, labels, alphas, sizes, shapes, colors}`, each a
dict keyed by AST node kind (e.g. `"FunctionDef"`, `"If"`) mapping to
that kind's style value.

### GET `/palette/custom?palette_id=<id>`

**There is no palette store, and this route says so.** It answers 200
with `results.unavailable: true`, the `requested` id echoed back, and a
`remedy` — the same convention `/topology/*` uses for a dependency that
is not there. Branch on `unavailable`; there is no `Palette` in the
response to mistake for a successful lookup.

---

## Web Application

### GET `/app`

The built web application from `web/dist`, with its API origin injected, or a
page saying there is no build and how to make one. `/` redirects here when a
build is present, and to `/docs` when it is not. Kept out of the schema.

---

## Response Format

Routes answer in `generate_return`'s envelope (`codecarto/util/utilities.py`):

```json
{
  "status": 200,
  "message": "route/action - Success",
  "results": { ... }
}
```

The estate routes put an absence inside a 200 (`results.unreadable` or
`results.unreachable`, with `problem`, `remedy` and `where`), because the route
worked and the thing it reads was not there.

### Error Response

A route that fails raises, and the server answers with the HTTP status and the
message alone (`main.py`'s `http_exception_handler`):

```json
{ "message": "Error description" }
```

Two answers do not pass through that handler. A path no route serves is
FastAPI's own 404, `{"detail": "Not Found"}`, and a request that fails
validation -- a parameter or body field missing, or of the wrong type -- is a 422,
`{"detail": [...]}`, one entry per field. A route that answers in the envelope can
also carry a status inside a 200: `DELETE /parse/cache/{key}` for a key the cache
does not hold answers HTTP 200 with `status: 404`.

### Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid params) |
| 404 | Not Found (missing file/dir, or a path no route serves) |
| 422 | Unprocessable Entity (a parameter or body field missing or of the wrong type) |
| 403 | Forbidden (GitHub rate limit) |
| 500 | Internal Server Error |
| 502 | Bad Gateway (GitHub download failed) |

---

## CORS

Allowed origins (configurable in `main.py`):
- `http://localhost:1234` (Vite dev / parcel)
- `http://localhost:1235` (Vite alt)

---

## Example Workflows

### Parse a GitHub Python repo (unified)

```bash
# 1. Fetch directory tree
curl "$API/repo/tree?url=https://github.com/user/myrepo"

# 2. Parse to depth-2 (symbols) with the unified parser
curl -X POST "$API/parse/unified" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": { <paste /repo/tree response data> },
    "depth": 2,
    "layout": "Spring"
  }'
```

### Check available language parsers

```bash
curl "$API/parse/languages"
# -> results.languages: { "python": [".py"], "c": [".c", ".h", ".cpp", ...], "rust": [".rs"], ... }
```

### Parse a local C directory (dedicated C-parser pipeline)

Use this when you want the legacy flat shape directly (e.g. scripting
against `meta.diagnostics`/`meta.skipped_files` without dealing with gJGF).
For the D3/Gravis UI, `/parse/unified` with `.c`/`.h` extensions produces
equivalent results in gJGF form instead.

```bash
curl -X POST "$API/c-parser/directory" \
  -H "Content-Type: application/json" \
  -d '{ "path": "/home/user/linux/kernel/sched", "max_files": 50 }'
```
