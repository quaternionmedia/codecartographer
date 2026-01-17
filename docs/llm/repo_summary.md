# Codecarto Repository Summary

> LLM-optimized summary for code understanding and generation tasks.

## Project Identity

- **Name:** Codecarto
- **Version:** 0.3.0
- **Purpose:** Source code visualization and graph analysis
- **License:** MIT
- **Language:** Python 3.10+

## Quick Context

```
Codecarto parses source code → generates NetworkX graphs → visualizes via Gravis
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python |
| Frontend | Vite, TypeScript |
| Graphs | NetworkX |
| Visualization | Gravis, mpld3 |
| Package Manager | UV |
| CLI | Click |

## Key Entry Points

| File | Purpose |
|------|---------|
| `codecarto/cli.py` | CLI commands (dev, serve, repo scan/graph) |
| `codecarto/main.py` | FastAPI app configuration |
| `codecarto/services/local_repo_service.py` | Local filesystem parsing |
| `codecarto/services/parser_service.py` | Parse orchestration |
| `codecarto/services/parsers/ASTs/python_custom_ast.py` | Python AST parsing |

## Directory Structure

```
codecartographer/
├── codecarto/              # Main Python package
│   ├── cli.py              # Click CLI
│   ├── main.py             # FastAPI app
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic
│   │   ├── local_repo_service.py
│   │   ├── github_service.py
│   │   ├── parser_service.py
│   │   └── parsers/        # AST/Dir/Dep parsers
│   ├── models/             # Pydantic models
│   └── util/               # Utilities
├── web/                    # Frontend
├── docs/                   # Documentation
└── pyproject.toml          # Project config
```

## Core Data Models

```python
class File(BaseModel):
    url: str = ""
    name: str = ""
    size: int = 0
    raw: str = ""  # File contents

class Folder(BaseModel):
    name: str = ""
    size: int = 0
    files: List[File] = []
    folders: List["Folder"] = []

class Directory(BaseModel):
    info: RepoInfo  # owner, name, url
    size: int = 0
    root: Folder
```

## CLI Commands

```bash
uv run codecarto dev                    # Start backend + frontend
uv run codecarto serve                  # Backend only
uv run codecarto repo scan .            # Scan local repo
uv run codecarto repo graph . -t ast    # Generate AST graph
uv run codecarto repo graph . -t dependency  # Import graph
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/local/scan` | GET | Scan local repo |
| `/local/graph/ast` | GET | AST graph |
| `/local/graph/dependency` | GET | Import graph |
| `/repo/tree` | GET | GitHub repo tree |
| `/parser/raw` | POST | Parse GitHub file |

## Graph Output Format

```python
# NetworkX DiGraph structure
graph.nodes(data=True)  # [(id, {type, name, ...}), ...]
graph.edges(data=True)  # [(src, dst, {relationship, ...}), ...]

# JSON serialization
{
    "nodes": [{"id": "n1", "type": "Function", "name": "main"}],
    "edges": [{"source": "n1", "target": "n2", "relationship": "calls"}]
}
```

## Node Types (AST)

- `Module` - Python file
- `Function` - Function definition
- `Class` - Class definition
- `Import` - Import statement
- `Name` - Variable reference
- `Call` - Function call
- `Constant` - Literal value

## Common Patterns

### Parse Local Repo
```python
from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST

directory = get_local_repo("/path/to/project")
parser = PythonCustomAST()
graph = parser.parse(directory.root)
```

### Add CLI Command
```python
@cli.command()
@click.argument("path")
def my_command(path):
    """Description."""
    # Implementation
```

### Add API Endpoint
```python
@Router.get("/endpoint")
async def my_endpoint(param: str):
    result = await some_service_call(param)
    return generate_return(200, "Success", result)
```

## Development Commands

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uv run codecarto dev
uv run codecarto lint --fix
```

## Key Dependencies

- `fastapi` - Web framework
- `click` - CLI framework
- `networkx` - Graph library
- `pydantic` - Data validation
- `gravis` - Graph visualization
- `uvicorn` - ASGI server

## Version History

- **0.3.0** - UV migration, local repo support, CLI improvements
- **0.2.0** - FastAPI backend, GitHub parsing, Gravis visualization
