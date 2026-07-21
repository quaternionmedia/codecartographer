# Services Documentation

Detailed documentation of Codecarto's service layer.

---

## Overview

Services contain the business logic, separated from HTTP routing (routers) and data structures (models).

```
services/
├── github_service.py          # GitHub API integration
├── local_repo_service.py      # Local filesystem parsing
├── unified_parser_service.py  # Depth-based parse orchestration (all languages)
├── cache_service.py           # Parsed-graph + repo-tree cache (filesystem + optional MongoDB)
├── c_parser_service.py        # C-specific parse orchestration (libclang)
├── lexicon_service.py         # Hand-authored language lexicons -> graph
├── graph_serializer.py        # Graph JSON serialization
├── position_service.py        # Node positioning
└── parsers/
    ├── language_parser.py     # LanguageParser Protocol + ParserRegistry
    ├── python_language_parser.py
    ├── c_language_parser.py
    ├── regex_language_parser.py  # 12-language regex adapter
    └── ASTs/
        └── python_custom_ast.py
```

`palette_router.py` reads palettes directly (`DefaultPalette` from
`models/plot_data.py`, or `DatabaseContext.fetch_palette_by_id` for
custom ones) — there's no dedicated `PaletteService`.

---

## LocalRepoService

**File:** `local_repo_service.py`

Parses local filesystem directories into Codecarto's data structures.

### Functions

#### `get_local_repo(path, extensions, exclude_dirs)`

Scan a local directory and build a Directory structure.

```python
from codecarto.services.local_repo_service import get_local_repo

directory = get_local_repo(
    path="/path/to/project",
    extensions=[".py", ".js"],
    exclude_dirs=[".git", "node_modules", "__pycache__"]
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | - | Path to directory |
| `extensions` | List[str] | `[".py"]` | Extensions to include |
| `exclude_dirs` | List[str] | See below | Directories to skip |

**Default exclusions:** `.git`, `.venv`, `venv`, `__pycache__`, `node_modules`, `.pytest_cache`, `.mypy_cache`, `dist`, `build`, `.eggs`, `*.egg-info`

**Returns:** `Directory` model with `info`, `size`, and `root` (Folder)

---

#### `get_file_stats(directory)`

Get statistics about files in a Directory.

```python
stats = get_file_stats(directory)
# {'total_files': 45, 'total_size': 156234, 'python_files': 45, 'folders': 12}
```

---

## GitHubService

**File:** `github_service.py`

Integrates with GitHub API to fetch repository contents.

### Functions

#### `get_raw_from_repo(url)`

Fetch a GitHub repository's directory tree, cached via `CacheService`
(see ARCHITECTURE.md's "Two C-parser caches"). On a cache miss, fetches the
full tree in two API calls (`fetch_tree_fast`, the Git Trees API) and then
fetches file content per the repo's size tier — full content for small
repos, structure only for medium repos, a shallow listing for huge ones.

```python
from codecarto.services.github_service import get_raw_from_repo

directory = await get_raw_from_repo("https://github.com/user/repo")
```

**Returns:** `Directory` (file contents present only for small repos)

---

#### `get_raw_from_url(url)`

Fetch raw content from a specific file URL.

```python
content = await get_raw_from_url(
    "https://raw.githubusercontent.com/user/repo/main/file.py"
)
```

**Returns:** File content as string

---

### GitHub Token

`resolve_github_token()`, cached by `get_github_token()` and used by
`create_headers()`. Resolution order (first non-empty wins):
`CC_GITHUB_TOKEN` env var → `gh auth token` (keyring) → `GITHUB_TOKEN`/
`GH_TOKEN` env vars → `/run/secrets/github_token` (Docker secret) →
unauthenticated. See `docs/qm/adr/DRAFT-github-token-resolution.md` for
why the order is keyring-before-env-var, and `GET /auth/github`
(`docs/api.md`) to inspect the resolved source at runtime.

---

## UnifiedParserService

**File:** `unified_parser_service.py`

The language-agnostic parse orchestrator behind `/parse/*`. Dispatches
each file to its registered `LanguageParser` (via `ParserRegistry`,
keyed by extension), walks folders to the requested depth, and — for
languages needing cross-file context (`batch_whole_tree = True`, e.g.
C) — batches all of that language's files into one parser call instead
of one-at-a-time. See `docs/llm/ARCHITECTURE.md` for the full pipeline.

### Methods

#### `parse(source, depth, extensions, layout)`

Parse a `Directory`/`Folder` structure at the given depth (1 =
dirs/files only, 2 = symbols and cross-file edges too).

```python
graph = UnifiedParserService.parse(directory, depth=2, extensions=None, layout="Spring")
```

**Returns:** gJGF-ready graph dict

---

#### `stream_parse(...)` / `stream_parse_url(...)` (async generators)

SSE variants of `parse()` — yield `meta`/`node`/`edge`/`done` events as
parsing progresses, for the local-directory and GitHub-URL cases
respectively. Cache-hit replay (`CacheService`) short-circuits both to
an instant replay of the saved graph.

#### `expand_node(...)`

Lazily expand a single node's children on demand (used by the
compound-hierarchical layout's drill-down).

---

## Parsers

### PythonCustomAST

**File:** `parsers/ASTs/python_custom_ast.py`

Parses Python source code into AST-based graph.

```python
from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST

parser = PythonCustomAST()
graph = parser.parse(folder)
```

**Node Types Generated:**

| Type | Description |
|------|-------------|
| `Module` | Python module (file) |
| `Function` | Function definition |
| `Class` | Class definition |
| `Import` | Import statement |
| `Name` | Variable/name reference |
| `Call` | Function call |
| `Constant` | Literal value |
| `Argument` | Function argument |

---

Directory/file hierarchy and Python import-dependency edges are both
produced by `UnifiedParserService` itself now (depth=1 for the
hierarchy; `_add_python_dependency_edges()` for `depends_on` edges at
depth>=2), not by separate parser classes.

---

## LexiconService

**File:** `lexicon_service.py`

Loads a hand-authored per-language lexicon (reserved words/operators on
a hierarchy of abstraction layers, from `data/lexicons/<language>.yaml`)
and projects it into the same graph pipeline the parsers use. See
`docs/llm/roadmap/lexicon.md` for the full design and the `/lexicon/*`
endpoints in `docs/api.md`.

### Methods

| Method | Description |
|--------|-------------|
| `available()` | List language ids with a lexicon on disk |
| `load(language)` | Load + validate a language's YAML into a `Lexicon` |
| `to_graph(lexicon)` | Project to an `nx.DiGraph` |
| `to_json(lexicon)` | Project to the node-link `{nodes, links}` shape the plotter consumes |

---

## CacheService

**File:** `cache_service.py`

Content-addressed cache for parsed graphs and fetched repo trees —
filesystem-backed, with an optional MongoDB backend when `MONGODB_URI`
is set. Key = `SHA256(url + mode + layout + extensions)[:16]`. Distinct
from `graphbase` (a separate, user-named durable store) — see
`docs/qm/adr/DRAFT-cache-service-vs-graphbase.md` for why they're kept
separate.

### Methods

| Method | Description |
|--------|-------------|
| `cache_key(url, mode, layout, extensions)` | Compute the cache key |
| `get(key)` / `set(key, ...)` | Read/write a cached parsed graph |
| `list_cached()` | List all cached entries |
| `evict(key)` | Remove one cached entry |
| `get_tree(url)` / `set_tree(url, data)` | Cache a fetched repo tree separately from parsed graphs |
| `evict_repo(url)` | Remove a cached repo tree |

---

## CParserService

**File:** `c_parser_service.py`

C-specific parse orchestration via libclang, used by the dedicated
`/c-parser/*` endpoints (distinct from C files going through the
generic `/parse/*` path via `c_language_parser.py` — see
`docs/llm/ARCHITECTURE.md`'s "Two C-parser caches").

### Methods

| Method | Description |
|--------|-------------|
| `parse_file(path)` | Parse a single C/H file |
| `parse_directory(path, ...)` | Parse a local directory, with an optional per-file progress callback |
| `parse_github(...)` | Parse a GitHub repo's C/H files |
| `list_cached_repos()` / `evict_repo_cache(key)` | Manage this service's own repo-tree cache |

---

## GraphSerializer

**File:** `graph_serializer.py`

Serializes NetworkX graphs to JSON format for client-side rendering.

### Methods

#### `serialize_to_gjgf(graph, options, isDependencyPlot)`

Convert NetworkX graph to Graph JSON Format (gJGF) with layout positions.

```python
from codecarto.services.graph_serializer import GraphSerializer

gjgf = GraphSerializer.serialize_to_gjgf(
    graph=nx_graph,
    options=plot_options,
    isDependencyPlot=False
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `graph` | `nx.DiGraph` | NetworkX directed graph |
| `options` | `PlotOptions` | Layout, type, palette settings |
| `isDependencyPlot` | `bool` | Whether to color external dependencies |

**Returns:** Graph in gJGF format with node positions and styling

#### `create_metadata(graph, options)`

Generate metadata about the graph.

```python
metadata = GraphSerializer.create_metadata(graph, options)
# {'layout': 'Spectral', 'type': 'd3', 'nodeCount': 50, 'edgeCount': 75}
```

**Layouts Available:**

| Layout | Description |
|--------|-------------|
| `Spring` | Force-directed (default) |
| `Circular` | Circular arrangement |
| `Shell` | Concentric circles |
| `Kamada_Kawai` | Energy-based layout |
| `Spectral` | Eigenvector-based |

**Client-side Rendering:** The gJGF format is consumed by the frontend D3.js renderer for interactive visualization.

---

## PositionService

**File:** `position_service.py`

Calculates node positions for graph layouts.

### Custom Layouts

Located in `models/custom_layouts/`:

| Layout | File | Description |
|--------|------|-------------|
| Arch | `arch_layout.py` | Hierarchical arch |
| Cluster | `cluster_layout.py` | Clustered groups |
| Sorted Square | `sorted_square_layout.py` | Grid arrangement |

---

## Creating New Services

### Template

```python
# services/my_service.py

class MyService:
    
    @staticmethod
    async def my_operation(param: str) -> dict:
        """
        Description of operation.
        
        Args:
            param: Description
            
        Returns:
            Result description
        """
        # Implementation
        result = {"key": "value"}
        return result
```

### Integration

1. Create service in `services/`
2. Import in router
3. Call from endpoint

```python
# routers/my_router.py

from fastapi import APIRouter
from codecarto.services.my_service import MyService

MyRouter = APIRouter()

@MyRouter.get("/operation")
async def my_endpoint(param: str):
    return await MyService.my_operation(param)
```

---

## Service Dependencies

```
┌─────────────────┐
│     Routers     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Services     │
│(UnifiedParser-  │
│Service, GraphSe-│
│rializer)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│    Parsers      │     │     Models      │
│ (PythonCustomAST│     │ (Directory,     │
│  via ParserReg- │     │  Graph, Plot)   │
│  istry)         │     │                 │
└─────────────────┘     └─────────────────┘
```

---

## Error Handling

Services use custom exceptions from `util/exceptions.py`:

```python
from codecarto.util.exceptions import CodeCartoException

class GithubError(CodeCartoException):
    pass

class Github404Error(GithubError):
    pass
```

### Exception Pattern

```python
try:
    result = await service_operation()
except CodeCartoException as exc:
    return proc_exception(exc.source, exc.message, exc.params, exc)
except Exception as exc:
    return proc_exception("operation", "Unexpected error", {}, exc)
```
