# Codecarto Development Guide

> **Version 0.3.0** - UV-based development workflow

## Overview

This document describes the modern Python development workflow using `uv` as the package manager and the Click CLI for development tasks.

## Project Structure

```
codecartographer/
├── codecarto/              # Main Python package
│   ├── __init__.py
│   ├── cli.py              # Click CLI entry point
│   ├── main.py             # FastAPI application
│   ├── database/           # Database utilities
│   ├── models/             # Pydantic models
│   ├── routers/            # FastAPI route handlers
│   ├── services/           # Business logic
│   │   ├── github_service.py
│   │   ├── local_repo_service.py  # NEW: Local repo parsing
│   │   ├── parser_service.py
│   │   ├── plotter_service.py
│   │   └── parsers/        # AST parsers
│   └── util/               # Utility functions
├── web/                    # Frontend (Vite + TypeScript)
├── graphbase/              # Database submodule
├── docs/                   # Documentation
│   └── llm/                # LLM-friendly docs
├── pyproject.toml          # Project configuration (PEP 621)
└── .gitignore              # Git ignore patterns
```

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 18+ (for frontend)
- Docker (optional, for database)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
git submodule init && git submodule update

# Create virtual environment with uv
uv venv

# Activate virtual environment
# Windows (Git Bash):
source .venv/Scripts/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Install frontend dependencies
cd web && npm install && cd ..
```

## CLI Commands

The `codecarto` CLI provides all development utilities. Use `uv run` to execute:

```bash
# Show all available commands
uv run codecarto --help

# Show version
uv run codecarto --version
```

### Development Commands

| Command | Description |
|---------|-------------|
| `uv run codecarto dev` | Start full dev environment (backend + frontend) |
| `uv run codecarto dev --no-frontend` | Start backend only in dev mode |
| `uv run codecarto serve` | Start API server only |
| `uv run codecarto web` | Start frontend only |

### Utility Commands

| Command | Description |
|---------|-------------|
| `uv run codecarto info` | Show project and environment info |
| `uv run codecarto parse FILE` | Parse a Python file |
| `uv run codecarto lint` | Run linter on codebase |
| `uv run codecarto lint --fix` | Auto-fix lint issues |

### Docker Commands

| Command | Description |
|---------|-------------|
| `uv run codecarto docker` | Start all Docker containers |
| `uv run codecarto docker-down` | Stop and remove containers |

## Development Workflow

### Quick Start (Recommended)

```bash
# Terminal 1: Start full dev environment
uv run codecarto dev
```

This starts:
- **Backend**: http://127.0.0.1:8000 (FastAPI with hot reload)
- **Frontend**: http://localhost:1234 (Vite dev server)
- **API Docs**: http://127.0.0.1:8000/docs

### Manual Start (Advanced)

```bash
# Terminal 1: Backend only
uv run codecarto serve --port 8000

# Terminal 2: Frontend only
uv run codecarto web
```

### With Docker (Full Stack)

```bash
# Start database containers
uv run codecarto docker

# Start dev servers
uv run codecarto dev

# When done
uv run codecarto docker-down
```

## Package Management with UV

### Adding Dependencies

```bash
# Add runtime dependency
uv pip install <package>

# Add dev dependency  
uv pip install <package>
# Then add to pyproject.toml [project.optional-dependencies.dev]

# Regenerate requirements.txt
uv pip compile pyproject.toml --all-extras -o requirements.txt
```

### Sync Environment

```bash
# Install from pyproject.toml
uv pip install -e ".[dev]"

# Or from requirements.txt
uv pip sync requirements.txt
```

## API Endpoints

The FastAPI backend provides these routers:

| Prefix | Description |
|--------|-------------|
| `/palette` | Color palette management |
| `/parser` | Source code parsing |
| `/plotter` | Graph visualization |
| `/polygraph` | Graph operations |
| `/repo` | GitHub repository reading |

Access interactive docs at http://127.0.0.1:8000/docs

## Local Repository Commands

Codecarto can parse local repositories without needing GitHub:

### CLI Commands

```bash
# Scan a local repo
uv run codecarto repo scan /path/to/project
uv run codecarto repo scan .                    # Current directory

# Show directory tree
uv run codecarto repo tree . -d 3               # Depth 3

# Generate graphs
uv run codecarto repo graph . -t ast            # AST graph
uv run codecarto repo graph . -t directory      # Directory graph
uv run codecarto repo graph . -t dependency     # Import dependencies

# Filter by extensions
uv run codecarto repo scan . -e .py -e .js

# JSON output
uv run codecarto repo scan . -o json
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /local/scan?path=...` | Scan repo structure |
| `GET /local/tree?path=...` | Get directory tree |
| `GET /local/graph/ast?path=...` | AST graph |
| `GET /local/graph/directory?path=...` | Directory graph |
| `GET /local/graph/dependency?path=...` | Dependency graph |

## Troubleshooting

### Virtual Environment Issues

```bash
# Recreate venv
rm -rf .venv
uv venv
source .venv/Scripts/activate  # Windows Git Bash
uv pip install -e ".[dev]"
```

### CLI Not Found

```bash
# Reinstall in editable mode
uv pip install -e .
```

### Port Already in Use

```bash
# Use different port
codecarto serve --port 8001
codecarto dev --port 8001
```

## Next Steps

1. **Add tests** - Run with `pytest`
2. **Improve linting** - Configure ruff in `pyproject.toml`
3. **CI/CD** - Add GitHub Actions workflow
4. **Frontend integration** - Connect local repo to web UI

## Changelog

### v0.3.0 (Current)
- Migrated from Poetry to UV package manager
- Added Click CLI with development commands
- Added local repository parsing (no GitHub required)
- Cleaned up duplicate code (removed `src/`, `build/`)
- Updated documentation structure

### v0.2.0
- Initial FastAPI backend
- GitHub repository parsing
- Gravis graph visualization

## Related Files

- [pyproject.toml](../../pyproject.toml) - Project configuration
- [cli.py](../../codecarto/cli.py) - CLI implementation
- [main.py](../../codecarto/main.py) - FastAPI app
- [local_repo_service.py](../../codecarto/services/local_repo_service.py) - Local repo parsing
