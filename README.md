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
uv run codecarto serve    # Backend only (http://127.0.0.1:8000)
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

Once the server is running, access:
- **API Docs**: http://127.0.0.1:8000/docs
- **Frontend**: http://localhost:1234

| Endpoint | Description |
|----------|-------------|
| `/palette` | Color palette management |
| `/parser` | Source code parsing |
| `/plotter` | Graph visualization |
| `/polygraph` | Graph operations |
| `/repo` | GitHub repository reading |
| `/local` | Local repository analysis |

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
├── web/                 # Frontend (Vite + TypeScript)
├── graphbase/           # Database submodule
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
```

## Docker (Optional)

```bash
# Start database containers
uv run codecarto docker

# Stop containers
uv run codecarto docker-down
```

## Documentation

- [Development Guide](docs/llm/uv_migration.md) - Full dev cycle documentation

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the development guide before submitting PRs.
