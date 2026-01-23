# Codecarto Documentation

> **Version 0.3.0** | Source code visualization and analysis tool

## Quick Links

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Installation and first steps |
| [CLI Reference](cli.md) | Complete command-line interface guide |
| [API Reference](api.md) | REST API endpoints and usage |
| [Architecture](architecture.md) | System design and components |
| [Services](services.md) | Service layer documentation |
| [Contributing](contributing.md) | Development guidelines |

## What is Codecarto?

Codecarto is a development tool that:

- **Parses** source code into structured graph representations
- **Visualizes** code structure, dependencies, and relationships
- **Analyzes** both local repositories and GitHub repos
- **Serves** interactive graph visualizations via web UI

## Quick Start

```bash
# Install
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
uv venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"

# Run
uv run codecarto dev
```

Open http://localhost:1234 for the web UI, http://127.0.0.1:8000/docs for API docs.

## Features

### Local Repository Analysis
```bash
uv run codecarto repo scan .           # Scan current directory
uv run codecarto repo graph . -t ast   # Generate AST graph
```

### GitHub Repository Analysis
```bash
# Via web UI or API
curl "http://127.0.0.1:8000/repo/tree?url=https://github.com/user/repo"
```

### Graph Types

| Type | Description | Use Case |
|------|-------------|----------|
| **AST** | Abstract Syntax Tree | Code structure analysis |
| **Directory** | File/folder hierarchy | Project overview |
| **Dependency** | Import relationships | Module coupling |

## Documentation Structure

```
docs/
├── index.md              # This file
├── getting-started.md    # Installation guide
├── cli.md                # CLI reference
├── api.md                # API reference
├── architecture.md       # System design
├── services.md           # Service documentation
├── contributing.md       # Dev guidelines
├── .diagrams/            # PlantUML diagrams
└── llm/                  # LLM-optimized docs
    ├── repo_summary.md   # Codebase summary
    └── uv_migration.md   # Dev workflow guide
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.10+ |
| **Frontend** | Vite, TypeScript |
| **Graphs** | NetworkX, Gravis |
| **Package Manager** | UV |
| **Database** | MongoDB (optional) |
