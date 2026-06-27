# API Reference

REST API documentation for Codecarto backend.

**Base URL:** `http://127.0.0.1:8000`
**Interactive Docs:** `http://127.0.0.1:8000/docs`

---

## Overview

| Prefix | Tag | Description |
|--------|-----|-------------|
| `/parse` | parse | **Unified parse (all languages, recommended)** |
| `/plotter` | plotter | Legacy graph visualization |
| `/parser` | parser | Legacy Python code parsing |
| `/c-parser` | c-parser | C/H semantic parsing (requires `[c-parsing]` optional dep) |
| `/repo` | repo | GitHub repository operations |
| `/local` | local | Local repository operations |
| `/pam` | pam | PAM auth log monitor |
| `/polygraph` | polygraph | Graph transformation operations |
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

## Legacy Plotter Endpoints

These endpoints are Python-only and use the older parser modes.

### POST `/plotter/whole_repo`

Parse an entire repository using a legacy parser mode.

**Request Body:**
```json
{
  "directory": { "info": {...}, "size": 0, "root": {...} },
  "options": {
    "palette_id": "0",
    "layout": "Spring",
    "type": "d3",
    "parse_by": "ast"
  }
}
```

**`parse_by` values:** `"ast"` | `"directory"` | `"dependencies"`

**Response:** gJGF `{ graph: {...}, metadata: {...} }` (same shape as `/parse/unified`)

---

### POST `/plotter/demo`

Generate a demo graph from the codecarto source code itself.

**Request Body:**
```json
{
  "options": { "palette_id": "0", "layout": "Spring", "type": "d3", "parse_by": "ast" }
}
```

---

### POST `/plotter/file`

Parse a single uploaded file.

**Request Body:**
```json
{
  "file": { "url": "", "name": "main.py", "size": 500, "raw": "def hello(): pass" },
  "options": { "palette_id": "0", "layout": "Spectral", "type": "d3", "parse_by": "ast" }
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
{ "path": "/absolute/path/to/file.c", "cache_dir": null }
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

> **Note:** `/c-parser/*` returns a legacy `{nodes, edges, meta}` dict. Use
> `/parse/unified` with `.c`/`.h` extensions to get gJGF output compatible with D3/Gravis.

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
  "max_files": 200,
  "cache_dir": null
}
```

---

### POST `/c-parser/github`

Download a GitHub repository and parse all C/H files.

**Request Body:**
```json
{ "url": "https://github.com/owner/repo", "max_files": 200 }
```

---

## GitHub Repository Endpoints

### GET `/repo/tree`

Fetch the top-level directory tree of a GitHub repository.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | GitHub repository URL |

**Example:**
```bash
curl "http://127.0.0.1:8000/repo/tree?url=https://github.com/fastapi/fastapi"
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
- Repos > 1 GB are rejected
- Requires GitHub token for private repos (place in `/run/secrets/github_token` or `token.txt`)

---

### GET `/repo/subtree`

Lazily expand a single folder path within a previously fetched repository.

**Query Parameters:** `url`, `path`

---

## Local Repository Endpoints

### GET `/local/scan`

Scan a local repository and return structure with statistics.

**Query Parameters:** `path`, `extensions` (array)

**Example:**
```bash
curl "http://127.0.0.1:8000/local/scan?path=/path/to/project&extensions=.py"
```

### GET `/local/tree`

Get directory tree structure for a local path.

**Query Parameters:** `path`, `extensions` (array)

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

## Polygraph Endpoints

Graph transformation utilities operating on in-memory graphs.

### POST `/polygraph/merge`

Merge two or more graphs into one.

### POST `/polygraph/filter`

Filter graph nodes by type or attribute predicate.

### POST `/polygraph/subgraph`

Extract a subgraph around a set of seed nodes.

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

### Parse a local C directory (legacy endpoint)

```bash
curl -X POST "http://127.0.0.1:8000/c-parser/directory" \
  -H "Content-Type: application/json" \
  -d '{ "path": "/home/user/linux/kernel/sched", "max_files": 50 }'
```
