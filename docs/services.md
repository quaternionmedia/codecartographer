# Services Documentation

Detailed documentation of Codecarto's service layer.

---

## Overview

Services contain the business logic, separated from HTTP routing (routers) and data structures (models).

```
services/
├── github_service.py       # GitHub API integration
├── local_repo_service.py   # Local filesystem parsing
├── palette_service.py      # Color management
├── parser_service.py       # Parse orchestration
├── graph_serializer.py     # Graph JSON serialization
├── polygraph_service.py    # Graph operations
├── position_service.py     # Node positioning
└── parsers/
    ├── ASTs/
    │   └── python_custom_ast.py
    └── python/
        ├── directory_parser.py
        └── dependency_parser.py
```

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

Fetch and parse a GitHub repository.

```python
from codecarto.services.github_service import get_raw_from_repo

directory = await get_raw_from_repo("https://github.com/user/repo")
```

**Returns:** `Directory` with full file contents

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

#### `get_repo_content(url, owner, repo, path)`

Fetch directory listing from GitHub API.

**Returns:** Dict with file/folder metadata

---

### GitHub Token

Reads from `/run/secrets/github_token` or `token.txt`:

```python
def create_headers(url):
    with open("/run/secrets/github_token", "r") as file:
        GIT_API_KEY = file.read().strip()
    return {"Authorization": f"token {GIT_API_KEY}"}
```

---

## ParserService

**File:** `parser_service.py`

Orchestrates parsing operations, delegating to specific parsers.

### Methods

#### `parse_raw(url)` (async)

Parse a file from GitHub URL.

```python
graph = await ParserService.parse_raw(
    "https://raw.githubusercontent.com/user/repo/main/file.py"
)
```

**Returns:** `nx.DiGraph` with AST nodes

---

#### `parse_code(folder)` (async)

Parse a Folder structure.

```python
graph = await ParserService.parse_code(folder)
```

---

#### `parse_directory(directory)` (async)

Generate directory structure graph.

```python
graph = await ParserService.parse_directory(directory)
```

**Returns:** Graph with folder/file hierarchy

---

#### `parse_dependancy(directory)` (async)

Generate import dependency graph.

```python
graph = await ParserService.parse_dependancy(directory)
```

**Returns:** Graph with import relationships

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

### DirectoryParser

**File:** `parsers/python/directory_parser.py`

Creates graph from directory structure.

```python
from codecarto.services.parsers.python.directory_parser import DirectoryParser

parser = DirectoryParser()
graph = parser.parse(directory)
```

**Node Types:**

| Type | Description |
|------|-------------|
| `Folder` | Directory node |
| `File` | File node |

**Edges:** Parent-child containment relationships

---

### DependencyParser

**File:** `parsers/python/dependency_parser.py`

Analyzes import statements to build dependency graph.

```python
from codecarto.services.parsers.python.dependency_parser import DependencyParser

parser = DependencyParser()
graph = parser.parse(directory)
```

**Node Types:**

| Type | Description |
|------|-------------|
| `Module` | Python module |
| `Package` | External package |

**Edges:** Import relationships

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

## PaletteService

**File:** `palette_service.py`

Manages color palettes for visualization.

### Methods

#### `get_palette(name)`

Get colors for a named palette.

#### `list_palettes()`

List available palette names.

---

## PolygraphService

**File:** `polygraph_service.py`

Graph manipulation operations.

### Operations

- **Merge:** Combine multiple graphs
- **Filter:** Extract nodes by type/attribute
- **Subgraph:** Extract neighborhood around nodes

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
│  (ParserService,│
│GraphSerializer) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│    Parsers      │     │     Models      │
│ (PythonCustomAST│     │ (Directory,     │
│  DependencyParser)    │  Graph, Plot)   │
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
