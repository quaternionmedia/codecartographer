# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│                    (http://localhost:1234)                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────────┐
│                      Frontend (Vite)                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  State   │  │Components│  │ Services │  │   Gravis     │    │
│  │ Manager  │  │   (UI)   │  │  (API)   │  │ (Rendering)  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API
┌─────────────────────────▼───────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                       Routers                            │    │
│  │  /palette  /parser  /plotter  /polygraph  /repo  /local │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Services                            │    │
│  │  ParserService  PlotterService  GitHubService  LocalRepo │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                       Parsers                            │    │
│  │  PythonCustomAST  DirectoryParser  DependencyParser      │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Models                              │    │
│  │  Directory  Folder  File  GraphData  PlotData            │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    Data Sources                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Local Files  │  │   GitHub     │  │   MongoDB (optional) │  │
│  │  (Filesystem)│  │     API      │  │     (graphbase)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Package Structure

```
codecarto/
├── __init__.py
├── cli.py              # Click CLI entry point
├── main.py             # FastAPI app configuration
│
├── routers/            # HTTP endpoint handlers
│   ├── palette_router.py
│   ├── parser_router.py
│   ├── plotter_router.py
│   ├── polygraph_router.py
│   ├── repo_router.py
│   └── local_repo_router.py
│
├── services/           # Business logic
│   ├── github_service.py
│   ├── local_repo_service.py
│   ├── palette_service.py
│   ├── parser_service.py
│   ├── plotter_service.py
│   ├── polygraph_service.py
│   ├── position_service.py
│   └── parsers/
│       ├── ASTs/
│       │   └── python_custom_ast.py
│       └── python/
│           ├── directory_parser.py
│           └── dependency_parser.py
│
├── models/             # Pydantic data models
│   ├── source_data.py      # File, Folder, Directory
│   ├── graph_data.py       # Graph structures
│   ├── plot_data.py        # Visualization data
│   ├── gravis_settings.py  # Gravis configuration
│   └── custom_layouts/     # NetworkX layouts
│
├── database/           # Database utilities
│   └── database.py
│
└── util/               # Utilities
    ├── exceptions.py
    └── utilities.py
```

## Data Flow

### 1. Source Code → Graph

```
Source Code (file/repo)
        │
        ▼
┌───────────────────┐
│  Local Repo or    │
│  GitHub Service   │
└─────────┬─────────┘
          │ Directory model
          ▼
┌───────────────────┐
│  Parser Service   │
│  (AST/Dir/Dep)    │
└─────────┬─────────┘
          │ NetworkX DiGraph
          ▼
┌───────────────────┐
│  Plotter Service  │
│  (Layout + Style) │
└─────────┬─────────┘
          │ PlotData
          ▼
┌───────────────────┐
│   Gravis/mpld3    │
│  (Visualization)  │
└───────────────────┘
```

### 2. Request Flow

```
HTTP Request
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Router    │────▶│   Service   │────▶│   Parser    │
│ (Endpoint)  │     │  (Logic)    │     │  (Process)  │
└─────────────┘     └─────────────┘     └─────────────┘
     │                                         │
     │◀────────────────────────────────────────┘
     │
     ▼
HTTP Response (JSON)
```

## Core Components

### CLI (`cli.py`)

Entry point for command-line operations using Click:

```python
@click.group()
def cli():
    """Codecarto CLI"""
    pass

@cli.command()
def dev():
    """Start development servers"""
    # Launches uvicorn + npm
```

### FastAPI App (`main.py`)

Configures the REST API:

```python
app = FastAPI()
app.add_middleware(CORSMiddleware, ...)
app.include_router(ParserRouter, prefix="/parser")
app.include_router(LocalRepoRouter, prefix="/local")
# ... more routers
```

### Routers

Handle HTTP requests and delegate to services:

| Router | Prefix | Purpose |
|--------|--------|---------|
| `PaletteRouter` | `/palette` | Color schemes |
| `ParserRouter` | `/parser` | Parse GitHub files |
| `PlotterRouter` | `/plotter` | Generate visualizations |
| `PolygraphRouter` | `/polygraph` | Graph operations |
| `RepoReaderRouter` | `/repo` | GitHub repos |
| `LocalRepoRouter` | `/local` | Local repos |

### Services

Business logic layer:

| Service | Responsibility |
|---------|---------------|
| `ParserService` | Orchestrates parsing |
| `GitHubService` | GitHub API integration |
| `LocalRepoService` | Local filesystem parsing |
| `PlotterService` | Graph layout and styling |
| `PositionService` | Node positioning algorithms |

### Parsers

Transform source code into graphs:

| Parser | Output |
|--------|--------|
| `PythonCustomAST` | AST nodes and edges |
| `DirectoryParser` | File hierarchy graph |
| `DependencyParser` | Import relationship graph |

### Models

Pydantic models for data validation:

```python
class File(BaseModel):
    url: str = ""
    name: str = ""
    size: int = 0
    raw: str = ""

class Folder(BaseModel):
    name: str = ""
    size: int = 0
    files: List[File] = []
    folders: List["Folder"] = []

class Directory(BaseModel):
    info: RepoInfo
    size: int = 0
    root: Folder
```

## Graph Representation

Codecarto uses NetworkX `DiGraph` for graph representation:

```python
import networkx as nx

G = nx.DiGraph()
G.add_node("module", type="Module", name="main.py")
G.add_node("func", type="Function", name="process")
G.add_edge("module", "func", relationship="contains")
```

### Node Attributes

| Attribute | Description |
|-----------|-------------|
| `type` | Node type (Module, Function, Class, etc.) |
| `name` | Display name |
| `line` | Source line number |
| `color` | Visualization color |

### Edge Attributes

| Attribute | Description |
|-----------|-------------|
| `relationship` | Edge type (contains, imports, calls) |
| `weight` | Edge weight for layout |

## Frontend Architecture

```
web/src/
├── index.html          # Entry point
├── index.ts            # Main TypeScript
├── components/         # UI components
├── services/           # API client services
├── state/              # State management
└── styles/             # CSS
```

## Database (Optional)

MongoDB integration via `graphbase` submodule:

- Stores parsed graphs
- Enables graph queries
- Caches analysis results

## Extension Points

### Adding a New Parser

1. Create parser in `services/parsers/`
2. Return `nx.DiGraph`
3. Add to `ParserService`
4. Create API endpoint in router

### Adding a New Visualization

1. Add layout in `models/custom_layouts/`
2. Update `PlotterService`
3. Configure Gravis settings

### Adding a CLI Command

1. Add function in `cli.py` with `@cli.command()` decorator
2. Use Click options/arguments for parameters

## Architecture Decision Records

For the *why* behind non-obvious structural choices (not just the *what*
described above), see [`docs/adr/`](adr/README.md).
