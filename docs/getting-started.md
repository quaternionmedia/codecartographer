# Getting Started

## Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **UV** - [Install](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js 18+** - [Download](https://nodejs.org/) (for frontend)
- **Git** - [Download](https://git-scm.com/)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer

# Initialize submodules
git submodule init
git submodule update
```

### 2. Create Virtual Environment

```bash
# Create venv with uv
uv venv

# Activate
# Linux/macOS:
source .venv/bin/activate

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Windows Git Bash:
source .venv/Scripts/activate
```

### 3. Install Dependencies

```bash
# Install Python packages (including dev dependencies)
uv pip install -e ".[dev]"

# Frontend dependencies are installed automatically by the CLI
# Or manually: cd web && npm install
```

### 4. Verify Installation

```bash
uv run codecarto --version
# codecarto, version 0.3.0

uv run codecarto info
# Shows Python version, dependencies, etc.
```

## Running Codecarto

### Quick Start (Recommended)

```bash
uv run codecarto dev
```

This starts the backend, on the port `codecarto.cli.DEFAULT_PORT` names (the
constant the corpus's `qm dashboard` allocates to this project; the command
prints it, with the `/docs` address), and the frontend on
`http://localhost:1234`. The port is deliberately not written here: five pages
once named a port the server had stopped binding.

Press `Ctrl+C` to stop both servers.

### Backend Only

```bash
uv run codecarto serve
# or with options:
uv run codecarto serve --host 0.0.0.0 --port 8080
```

### Frontend Only

```bash
uv run codecarto web
```

## First Analysis

### Analyze a Local Repository

```bash
# Scan structure
uv run codecarto repo scan /path/to/project

# Generate graph
uv run codecarto repo graph /path/to/project -t ast
```

### Analyze via Web UI

1. Open http://localhost:1234
2. Enter a GitHub repo URL (e.g., `https://github.com/fastapi/fastapi`)
3. Click Submit
4. Browse files and click to visualize

### Analyze via API

```bash
# $API is the backend address `codecarto serve` printed

# The tree of a local directory (the same route reads a GitHub URL)
curl "$API/repo/tree?url=/path/to/project"

# Every seam this window reads, and whether each is there
curl "$API/estate/seams"
```

`docs/api.md` is the map of the routes; `$API/docs` is the authority.

## GitHub Token (Optional)

For analyzing GitHub repositories, create a personal access token:

1. Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
2. Generate new token with `public_repo` scope
3. Create `token.txt` in project root:
   ```
   ghp_your_token_here
   ```

## Docker (Optional)

For database functionality:

```bash
# Start containers
uv run codecarto docker

# Stop containers
uv run codecarto docker-down
```

## Next Steps

- [CLI Reference](cli.md) - All available commands
- [API Reference](api.md) - REST endpoints
- [Architecture](architecture.md) - How it works
