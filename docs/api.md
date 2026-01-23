# API Reference

REST API documentation for Codecarto backend.

**Base URL:** `http://127.0.0.1:8000`  
**Interactive Docs:** `http://127.0.0.1:8000/docs`

---

## Overview

| Prefix | Tag | Description |
|--------|-----|-------------|
| `/local` | local | Local repository operations |
| `/repo` | repo | GitHub repository operations |
| `/parser` | parser | Source code parsing |
| `/plotter` | plotter | Graph visualization |
| `/polygraph` | polygraph | Graph operations |
| `/palette` | palette | Color palette management |

---

## Local Repository Endpoints

### GET `/local/scan`

Scan a local repository and return structure with statistics.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Absolute path to repository |
| `extensions` | array[string] | No | `[".py"]` | File extensions to include |

**Example Request:**
```bash
curl "http://127.0.0.1:8000/local/scan?path=/path/to/project&extensions=.py&extensions=.js"
```

**Response:**
```json
{
  "code": 200,
  "message": "scan_local_repo - Success",
  "data": {
    "info": {
      "owner": "username",
      "name": "project",
      "url": "/path/to/project"
    },
    "stats": {
      "total_files": 45,
      "total_size": 156234,
      "python_files": 45,
      "folders": 12
    },
    "structure": {
      "name": "project",
      "size": 156234,
      "files": [...],
      "folders": [...]
    }
  }
}
```

---

### GET `/local/tree`

Get directory tree structure.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to repository |
| `extensions` | array[string] | No | `[".py"]` | Extensions to include |

**Example Request:**
```bash
curl "http://127.0.0.1:8000/local/tree?path=/path/to/project"
```

**Response:**
```json
{
  "code": 200,
  "message": "get_local_repo_tree - Success",
  "data": {
    "info": {
      "owner": "username",
      "name": "project",
      "url": "/path/to/project"
    },
    "root": {
      "name": "project",
      "size": 156234,
      "files": [
        {"name": "main.py", "size": 1234, "url": "/path/to/project/main.py", "raw": "..."}
      ],
      "folders": [
        {"name": "src", "size": 45000, "files": [...], "folders": [...]}
      ]
    }
  }
}
```

---

### GET `/local/graph/ast`

Generate AST graph from local repository.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to repository |
| `extensions` | array[string] | No | `[".py"]` | Extensions to include |

**Example Request:**
```bash
curl "http://127.0.0.1:8000/local/graph/ast?path=/path/to/project"
```

**Response:**
```json
{
  "code": 200,
  "message": "get_local_repo_ast_graph - Success",
  "data": {
    "name": "project",
    "nodes": [
      {"id": "node_1", "type": "Module", "name": "main.py"},
      {"id": "node_2", "type": "Function", "name": "process"}
    ],
    "edges": [
      {"source": "node_1", "target": "node_2", "relationship": "contains"}
    ]
  }
}
```

---

### GET `/local/graph/directory`

Generate directory structure graph.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to repository |
| `extensions` | array[string] | No | `[".py"]` | Extensions to include |

**Example Request:**
```bash
curl "http://127.0.0.1:8000/local/graph/directory?path=/path/to/project"
```

---

### GET `/local/graph/dependency`

Generate import dependency graph.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to repository |
| `extensions` | array[string] | No | `[".py"]` | Extensions to include |

**Example Request:**
```bash
curl "http://127.0.0.1:8000/local/graph/dependency?path=/path/to/project"
```

---

## GitHub Repository Endpoints

### GET `/repo/tree`

Get directory tree from a GitHub repository.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | GitHub repository URL |

**Example Request:**
```bash
curl "http://127.0.0.1:8000/repo/tree?url=https://github.com/fastapi/fastapi"
```

**Response:**
```json
{
  "code": 200,
  "message": "read_github_url - Success",
  "data": {
    "info": {
      "owner": "fastapi",
      "name": "fastapi",
      "url": "https://github.com/fastapi/fastapi"
    },
    "size": 1234567,
    "root": {
      "name": "fastapi/fastapi",
      "files": [...],
      "folders": [...]
    }
  }
}
```

**Notes:**
- Requires GitHub token for private repos
- Large repos (>1GB) are rejected

---

## Parser Endpoints

### POST `/parser/raw`

Parse raw source code from a GitHub URL.

**Request Body:**
```json
{
  "url": "https://raw.githubusercontent.com/user/repo/main/file.py"
}
```

**Response:**
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "name": "file.py",
    "nodes": [...],
    "edges": [...]
  }
}
```

---

### POST `/parser/code`

Parse source code from a Folder structure.

**Request Body:**
```json
{
  "folder": {
    "name": "root",
    "size": 1234,
    "files": [
      {"name": "main.py", "size": 1234, "raw": "def main(): pass"}
    ],
    "folders": []
  }
}
```

---

## Plotter Endpoints

### POST `/plotter/plot`

Generate visualization data for a graph.

**Request Body:**
```json
{
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "layout": "spring",
  "settings": {
    "node_size": 10,
    "edge_width": 1
  }
}
```

**Response:**
```json
{
  "code": 200,
  "data": {
    "html": "<div>...</div>",
    "positions": {...}
  }
}
```

---

## Polygraph Endpoints

### POST `/polygraph/merge`

Merge multiple graphs.

### POST `/polygraph/filter`

Filter graph by node type or attributes.

### POST `/polygraph/subgraph`

Extract subgraph around specific nodes.

---

## Palette Endpoints

### GET `/palette/list`

List available color palettes.

**Response:**
```json
{
  "palettes": ["default", "dark", "light", "colorblind"]
}
```

### GET `/palette/{name}`

Get specific palette colors.

---

## Response Format

All endpoints return a consistent response format:

### Success Response

```json
{
  "code": 200,
  "message": "operation - Success",
  "data": { ... }
}
```

### Error Response

```json
{
  "code": 400,
  "message": "Error description",
  "data": {
    "source": "function_name",
    "params": { ... }
  }
}
```

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request |
| 404 | Not Found |
| 403 | Forbidden (rate limit) |
| 500 | Internal Server Error |

## Rate Limiting

GitHub API has rate limits:
- **Without token:** 60 requests/hour
- **With token:** 5000 requests/hour

## CORS

Allowed origins:
- `http://localhost:1234` (frontend)
- `http://localhost:5000` (development)

## Authentication

### GitHub Token

For GitHub operations, place token in `/run/secrets/github_token` (Docker) or `token.txt` (local).

---

## Example Workflows

### Analyze Local Project

```bash
# 1. Scan structure
curl "http://127.0.0.1:8000/local/scan?path=/my/project"

# 2. Generate AST graph
curl "http://127.0.0.1:8000/local/graph/ast?path=/my/project"

# 3. Generate dependency graph
curl "http://127.0.0.1:8000/local/graph/dependency?path=/my/project"
```

### Analyze GitHub Repository

```bash
# 1. Get repo tree
curl "http://127.0.0.1:8000/repo/tree?url=https://github.com/user/repo"

# 2. Parse specific file
curl -X POST "http://127.0.0.1:8000/parser/raw" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://raw.githubusercontent.com/user/repo/main/main.py"}'
```

### Using with JavaScript

```javascript
// Fetch local repo graph
const response = await fetch(
  'http://127.0.0.1:8000/local/graph/ast?path=/my/project'
);
const data = await response.json();

// Process nodes
data.data.nodes.forEach(node => {
  console.log(`${node.type}: ${node.name}`);
});
```
