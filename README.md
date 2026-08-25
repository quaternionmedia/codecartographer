# Codecarto

**Development tool for mapping and visualizing source code as graphs.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Codecarto parses source code and generates interactive graph visualizations, helping developers understand code structure, dependencies, and relationships.

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+ (for frontend)

### Installation

```bash
# Clone the repository
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
git submodule init && git submodule update

# Create virtual environment and install
uv venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows PowerShell
# source .venv/Scripts/activate  # Windows Git Bash

uv pip install -e ".[dev]"
```

### Start Development

```bash
# Start full dev environment (backend + frontend)
uv run codecarto dev

# Or start components separately
uv run codecarto serve    # Backend only — `serve --help` names the default port
uv run codecarto web      # Frontend only (http://localhost:1234)
```

## CLI Commands

```bash
# Development
uv run codecarto dev              # Start backend + frontend
uv run codecarto serve            # Start API server
uv run codecarto web              # Start frontend

# Local Repository Analysis
uv run codecarto repo scan .      # Scan repo structure
uv run codecarto repo tree .      # Display directory tree
uv run codecarto repo graph .     # Generate code graph

# Utilities
uv run codecarto parse FILE       # Parse a Python file
uv run codecarto info             # Show environment info
uv run codecarto lint             # Run linter

# Docker
uv run codecarto docker           # Start containers
uv run codecarto docker-down      # Stop containers
```

### Local Repo Commands

```bash
# Scan with different extensions
uv run codecarto repo scan . -e .py -e .js

# Generate different graph types
uv run codecarto repo graph . -t ast         # AST graph (default)
uv run codecarto repo graph . -t directory   # Directory structure
uv run codecarto repo graph . -t dependency  # Import dependencies

# Output as JSON
uv run codecarto repo scan . -o json
```

## API Endpoints

Once the server is running, `/docs` on the backend's own origin lists every
route it actually registered — that is the authority, and this table is a map
of the neighbourhoods rather than a copy of it. `codecarto dev` prints both
addresses on startup; `serve --help` names the backend's default port.

| Endpoint | Description |
|----------|-------------|
| `/app` | The web application, served from `web/dist` when a build is present |
| `/palette` | Color palette management |
| `/parse` | Source code parsing, every supported language |
| `/plotter` | Graph visualization |
| `/repo` | GitHub repository reading |
| `/c-parser` | C parsing via libclang, plus a standalone visualizer page |
| `/pam` | PAM session capture, replay, and a standalone visualizer page |
| `/lexicon` | Hand-authored language lexicons, as graphs |
| `/topology` | The harness's flows as graph data, plus a build-free page |
| `/capabilities` | What each named thing this estate can do has reached |
| `/db` | Graphbase — mounted only when `MONGODB_URI` is set |

During `npm run dev` the Vite server proxies API prefixes to the backend, so the
app and its API share an origin exactly as they do in production. `API_PATHS` in
`web/vite.config.js` is the list that decides which — it does not cover every
row above, and a prefix missing from it is a request the dev server tries to
answer itself and cannot.

## Project Structure

```
codecartographer/
├── codecarto/           # Main Python package
│   ├── cli.py           # CLI entry point
│   ├── main.py          # FastAPI application
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic
│   ├── models/          # Pydantic models
│   └── util/            # Utilities
│   └── static/          # Standalone visualizer pages served by their routers
├── web/                 # Frontend (Vite + TypeScript)
├── tests/               # Python test suite
├── graphbase/           # Database submodule
├── governance/qm/       # Governance submodule — decision records live in adr/
├── docs/                # Documentation
└── pyproject.toml       # Project configuration
```

## GitHub Token (Optional)

For parsing public GitHub repositories:

1. Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
2. Generate a new token with `public_repo` scope
3. Create `token.txt` in the project root with your token

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run linter
uv run codecarto lint
uv run codecarto lint --fix   # Auto-fix issues

# Run backend tests
uv run pytest

# Run frontend end-to-end tests (starts the backend and frontend dev
# servers automatically — see web/playwright.config.ts)
cd web && npm run test:e2e

# Type-check the frontend (also runs automatically before `npm run build`)
cd web && npm run typecheck
```

## Docker (Optional)

```bash
# Start database containers
uv run codecarto docker

# Stop containers
uv run codecarto docker-down
```

## Documentation

- [Getting Started](docs/getting-started.md) — install, run, first graph
- [Architecture](docs/architecture.md) — how the pieces fit
- [CLI](docs/cli.md) and [API](docs/api.md) — the two command surfaces
- [Contributing](docs/contributing.md) — working on this project
- [UI Reference](docs/llm/UI_REFERENCE.md) — panels, renderers, and both radial menus

Decision records live on the `governance/qm` submodule, under `adr/`.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the development guide before submitting PRs.
