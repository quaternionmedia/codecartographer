# API Reference

REST API documentation for Codecarto backend.

**Base URL:** `http://127.0.0.1:8000`
**Interactive Docs:** `http://127.0.0.1:8000/docs`

---

## Overview

| Prefix | Tag | Description |
|--------|-----|-------------|
| `/parse` | parse | **Unified parse (all languages, recommended)** |
| `/plotter` | plotter | Demo data + Notebook-renderer HTML pre-render |
| `/c-parser` | c-parser | C/H semantic parsing (requires `[c-parsing]` optional dep) |
| `/repo` | repo | GitHub + local repository tree operations |
| `/pam` | pam | PAM auth log monitor |
| `/palette` | palette | Color palette management |

---

## Unified Parse Endpoints

These are the recommended endpoints. They work across all registered languages
(.py via Python parser, .c/.h via C parser) and produce gJGF output that any renderer
can display.

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
  "layout": "Spring"
}
```

**depth values:**
| depth | output |
|-------|--------|
| 0 | directories only |
| 1 | directories + files |
| 2 | + top-level symbols (class, function, struct, …) |
| 3 | + sub-symbols (arguments, fields, enum constants) |

**Response:**
```json
{
  "code": 200,
  "message": "parse/unified - Success",
  "data": {
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
| `node` | flat node dict (`id` + unified schema fields) | once per node |
| `edge` | `{source, target, label?, ...}` | once per edge, after all nodes |
| `done` | `{elapsed_ms, from_cache?}` | last |
| `error` | `{message}` | on exception, in place of `done` |

If the request matches a cached graph, all events are replayed instantly
from the cache (`from_cache: true`) instead of re-parsing.

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
file's content is fetched and parsed.

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

List all registered language parsers and their file extensions.

**Response:**
```json
{
  "code": 200,
  "message": "parse/languages - Success",
  "data": {
    "languages": {
      "python": [".py"],
      "c": [".c", ".h"]
    }
  }
}
```

---

## Plotter Endpoints

Only two routes remain here — the rest of `/plotter/*` (`whole_repo`,
`whole_repo_deps`, `folder`, `file`, `url`, `local_directory`) were dead
code (zero frontend callers, fully superseded by `/parse/unified`) and were
removed in the parser/cache unification pass. Use `/parse/unified` for
parsing; these two are demo/rendering utilities, not parse entry points.

### POST `/plotter/demo`

Generate a demo graph from the codecarto source code itself.

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
  "code": 200,
  "data": { "text/html": "<html>...</html>" }
}
```

---

## C Parser Endpoints

Require the optional `[c-parsing]` dependency group (libclang).
Install with: `uv pip install 'codecarto[c-parsing]'`

### POST `/c-parser/file`

Parse a single C/H source file.

**Request Body:**
```json
{ "path": "/absolute/path/to/file.c" }
```

**Response:**
```json
{
  "code": 200,
  "data": {
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

> **Note:** `/c-parser/*` returns a legacy flat `{nodes, edges, meta}` dict, not
> gJGF — the frontend's `adaptCGraphToGJGF` converts it. `/parse/unified` with
> `.c`/`.h` extensions produces gJGF natively and, since the unification pass,
> the *same* cross-file CALLS resolution, stub-header diagnostics, and
> `has_parse_warning` flagging as this dedicated pipeline — both call into the
> same `CParser` engine (per-symbol extras like `field_count`/`qualifiers`
> live under each unified node's `meta` field instead of top-level). Prefer
> `/parse/unified` unless you specifically need this legacy flat shape.

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

Streamed variant of `/c-parser/github`, used by the "C" example chips
(git, curl, Lua, SQLite, Redis) in earlier frontend builds. The current
web UI routes those chips through the unified `/parse/stream-url` flow;
this endpoint remains available for direct/manual callers. libclang parsing
is synchronous CPU-bound work, so it runs in a background thread while this
endpoint drains its progress queue and forwards SSE events in real time —
see "C semantic stream path" in `docs/llm/ARCHITECTURE.md` for the full
design rationale.

**Request Body:** same as `/c-parser/github`.

**Response:** `Content-Type: text/event-stream`:

| event | payload | when |
|-------|---------|------|
| `fetching` | `{message}` | during archive download/extract (skipped on cache hit) |
| `meta` | `{fileCount, skippedCount}` | once the target file list is known, before parsing starts |
| `node` | flat node dict + `language: "c"`, `depth: 2` | streamed file-by-file as libclang finishes each one |
| `edge` | `{source, target, label, weight}` | **all at once, after `node` events** — see below |
| `done` | `{elapsed_ms, node_count, edge_count, diagnostics, skipped_files}` | last |
| `error` | `{message}` | on exception, in place of `done` |

**Why nodes stream but edges arrive in one batch:** declarations (pass 1)
are parsed and emitted one file at a time, so nodes appear as libclang
works through the file list. Call edges and derived type edges
(FIELD_OF/POINTS_TO) need the *complete* cross-file node set to resolve
their targets, so they can only be computed — and streamed — after every
file's declarations are in.

---

### GET `/c-parser/cache`

List extracted GitHub repos in the C-parser's repo cache (newest first).
This is a *different* cache from `GET /parse/cache` — that one lists cached
*parsed graphs*; this one lists cached *extracted source trees* (downloaded
zip contents, re-parsed fresh on every request — only the download+extract
step is skipped on a hit). See `docs/llm/ARCHITECTURE.md`'s "Two C-parser
caches" for why these aren't merged into one.

**Response:**
```json
{
  "code": 200,
  "data": {
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
curl -X DELETE "http://127.0.0.1:8000/c-parser/cache/git-git"
```

---

## Repository Endpoints

Handle both GitHub URLs and local filesystem paths — `url` is checked
against `'github.com' in url` (see `github_service.is_github_url`) to decide
which backend (`github_service.py` vs `local_repo_service.py`) handles the
request. There is no separate set of local-only endpoints.

### GET `/repo/tree`

Fetch the directory tree of a GitHub repository **or** a local path.

For GitHub URLs, the result is cached (see "Two C-parser caches" in
ARCHITECTURE.md for the cache layout) — a repeat call for the same repo
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
curl "http://127.0.0.1:8000/repo/tree?url=https://github.com/fastapi/fastapi"
curl "http://127.0.0.1:8000/repo/tree?url=/path/to/local/project"
```

**Response:**
```json
{
  "code": 200,
  "message": "read_github_url - Success",
  "data": {
    "info": { "owner": "fastapi", "name": "fastapi", "url": "..." },
    "size": 1234567,
    "root": { "name": "fastapi", "files": [...], "folders": [...] },
    "is_partial": false
  }
}
```

**Notes:**
- GitHub: repos > 1 GB are rejected; requires a token for private repos
  (place in `/run/secrets/github_token` or `token.txt`)
- Local: default extension filter is every extension `ParserRegistry`
  knows about (not just `.py`); default excludes `.git`, `.venv`,
  `node_modules`, `.vs`, `.idea`, `bin`, `obj`, etc. (see
  `local_repo_service.get_local_repo`)

---

### GET `/repo/subtree`

Lazily expand a single folder path within a previously fetched repository
(GitHub or local).

**Query Parameters:** `url`, `path`

---

## PAM Monitor Endpoints

### GET `/pam/ui`

Serve the PAM auth log monitor HTML frontend (URL-patched for current server).

### GET `/pam/status`

Check PAM monitor status (running, log source, event count).

### WebSocket `/pam/ws/live`

Stream real-time PAM events as JSON objects:
```json
{ "timestamp": "...", "user": "alice", "event_type": "accepted", "rhost": "192.168.1.10" }
```

---

---

## Palette Endpoints

### GET `/palette/list`

List all available color palette IDs.

### GET `/palette/{id}`

Get a specific palette definition (bases, colors, shapes, sizes).

---

## Response Format

All endpoints use a consistent envelope:

```json
{
  "code": 200,
  "message": "route/action - Success",
  "data": { ... }
}
```

### Error Response
```json
{
  "code": 404,
  "message": "Error description",
  "data": { "source": "function_name", "params": { ... } }
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid params) |
| 404 | Not Found (missing file/dir) |
| 403 | Forbidden (GitHub rate limit) |
| 500 | Internal Server Error |
| 502 | Bad Gateway (GitHub download failed) |

---

## CORS

Allowed origins (configurable in `main.py`):
- `http://localhost:1234` (Vite dev / parcel)
- `http://localhost:1235` (Vite alt)
- `http://localhost:5000` (development tools)

---

## Example Workflows

### Parse a GitHub Python repo (unified)

```bash
# 1. Fetch directory tree
curl "http://127.0.0.1:8000/repo/tree?url=https://github.com/user/myrepo"

# 2. Parse to depth-2 (symbols) with the unified parser
curl -X POST "http://127.0.0.1:8000/parse/unified" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": { <paste /repo/tree response data> },
    "depth": 2,
    "layout": "Spring"
  }'
```

### Check available language parsers

```bash
curl "http://127.0.0.1:8000/parse/languages"
# -> { "languages": { "python": [".py"], "c": [".c", ".h"] } }
```

### Parse a local C directory (dedicated C-parser pipeline)

Use this when you want the legacy flat shape directly (e.g. scripting
against `meta.diagnostics`/`meta.skipped_files` without dealing with gJGF).
For the D3/Gravis UI, `/parse/unified` with `.c`/`.h` extensions produces
equivalent results in gJGF form instead.

```bash
curl -X POST "http://127.0.0.1:8000/c-parser/directory" \
  -H "Content-Type: application/json" \
  -d '{ "path": "/home/user/linux/kernel/sched", "max_files": 50 }'
```
