# CLI Reference

Complete reference for the `codecarto` command-line interface.

## Usage

```bash
uv run codecarto [OPTIONS] COMMAND [ARGS]...
```

## Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--help` | Show help message and exit |

---

## Development Commands

### `dev`

Start the full development environment (backend + frontend).

```bash
uv run codecarto dev [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Backend host address |
| `--port` | `8000` | Backend port |
| `--no-frontend` | `false` | Skip starting frontend |

**Examples:**

```bash
# Start full environment
uv run codecarto dev

# Backend only
uv run codecarto dev --no-frontend

# Custom port
uv run codecarto dev --port 8080

# Expose to network
uv run codecarto dev --host 0.0.0.0
```

**Output:**
- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:1234
- API Docs: http://127.0.0.1:8000/docs

---

### `serve`

Start the FastAPI backend server only.

```bash
uv run codecarto serve [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Host address |
| `--port` | `8000` | Port number |
| `--reload/--no-reload` | `--reload` | Enable hot reload |

**Examples:**

```bash
# Default
uv run codecarto serve

# Production mode (no reload)
uv run codecarto serve --no-reload

# Custom host/port
uv run codecarto serve --host 0.0.0.0 --port 8080
```

---

### `web`

Start the frontend development server only.

```bash
uv run codecarto web
```

Runs `npm run dev` in the `web/` directory. Frontend available at http://localhost:1234.

---

## Local Repository Commands

### `repo`

Group command for local repository operations.

```bash
uv run codecarto repo [COMMAND]
```

**Subcommands:**

| Command | Description |
|---------|-------------|
| `scan` | Scan repository structure |
| `tree` | Display directory tree |
| `graph` | Generate code graph |

---

### `repo scan`

Scan a local repository and show structure statistics.

```bash
uv run codecarto repo scan [PATH] [OPTIONS]
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `PATH` | `.` | Path to repository |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-e, --ext` | `.py` | File extensions to include (repeatable) |
| `-o, --output` | `text` | Output format: `text` or `json` |

**Examples:**

```bash
# Scan current directory
uv run codecarto repo scan .

# Scan specific path
uv run codecarto repo scan /path/to/project

# Multiple extensions
uv run codecarto repo scan . -e .py -e .js -e .ts

# JSON output
uv run codecarto repo scan . -o json
```

**Output (text):**
```
📂 Scanning: /path/to/project
  Extensions: .py

  Repository: owner/project
  Path: /path/to/project

  Statistics:
    Total files: 45
    Python files: 45
    Folders: 12
    Total size: 156.2 KB
```

---

### `repo tree`

Display directory tree of a local repository.

```bash
uv run codecarto repo tree [PATH] [OPTIONS]
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `PATH` | `.` | Path to repository |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-e, --ext` | `.py` | File extensions to include (repeatable) |
| `-d, --depth` | `3` | Maximum depth to display |

**Examples:**

```bash
# Default depth
uv run codecarto repo tree .

# Shallow tree
uv run codecarto repo tree . -d 1

# Deep tree with multiple extensions
uv run codecarto repo tree . -d 5 -e .py -e .md
```

**Output:**
```
🌳 Directory tree: /path/to/project

├── src/
│   ├── __init__.py (0.0 B)
│   ├── main.py (2.3 KB)
│   └── utils/
│       └── ...
└── tests/
    └── test_main.py (1.1 KB)
```

---

### `repo graph`

Generate a graph from a local repository.

```bash
uv run codecarto repo graph [PATH] [OPTIONS]
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `PATH` | `.` | Path to repository |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-e, --ext` | `.py` | File extensions to include (repeatable) |
| `-o, --output` | `text` | Output format: `text` or `json` |
| `-t, --type` | `ast` | Graph type: `ast`, `directory`, or `dependency` |

**Graph Types:**

| Type | Description |
|------|-------------|
| `ast` | Abstract Syntax Tree - code structure |
| `directory` | File/folder hierarchy |
| `dependency` | Import relationships |

**Examples:**

```bash
# AST graph (default)
uv run codecarto repo graph .

# Directory structure graph
uv run codecarto repo graph . -t directory

# Dependency graph
uv run codecarto repo graph . -t dependency

# JSON output for processing
uv run codecarto repo graph . -t ast -o json
```

**Output (text):**
```
📊 Generating ast graph: /path/to/project

  Graph: project
  Type: ast
  Nodes: 234
  Edges: 456

  Node types:
    - Constant: 89
    - Name: 67
    - Function: 23
    - Import: 18
    ...
```

---

## Utility Commands

### `parse`

Parse a single Python file and display code structure.

```bash
uv run codecarto parse FILE [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `FILE` | Path to Python file (must exist) |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `text` | Output format: `text` or `json` |

**Examples:**

```bash
# Parse file
uv run codecarto parse myfile.py

# JSON output
uv run codecarto parse myfile.py -o json
```

---

### `info`

Show project and environment information.

```bash
uv run codecarto info
```

**Output:**
```
📦 Codecarto Project Info

  Python:     3.13.3
  Platform:   Windows 11
  Repo root:  /path/to/codecartographer

  Virtual env: /path/to/.venv

  Dependencies:
    ✓ fastapi: 0.128.0
    ✓ networkx: 3.6.1
    ✓ click: 8.3.1
    ✓ gravis: 0.1.0
    ✓ uvicorn: 0.40.0
```

---

### `lint`

Run linting on the codebase using ruff.

```bash
uv run codecarto lint [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--fix` | Auto-fix issues |

**Examples:**

```bash
# Check for issues
uv run codecarto lint

# Auto-fix issues
uv run codecarto lint --fix
```

---

## Docker Commands

### `docker`

Start Docker containers for development.

```bash
uv run codecarto docker
```

Starts both `graphbase` and `codecarto` containers using docker-compose.

---

### `docker-down`

Stop and remove Docker containers.

```bash
uv run codecarto docker-down
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Command line usage error |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DEBUG` | Enable debug output for errors |
| `VIRTUAL_ENV` | Virtual environment path |

## Tips

### Running Without `uv run`

If you have the virtual environment activated:
```bash
source .venv/bin/activate  # or .venv\Scripts\activate
codecarto --help
```

### Piping JSON Output

```bash
# Parse to jq
uv run codecarto repo scan . -o json | jq '.stats'

# Save to file
uv run codecarto repo graph . -o json > graph.json
```

### Combining with Other Tools

```bash
# Find large Python files
uv run codecarto repo scan . -o json | jq '.structure.files[] | select(.size > 10000)'

# Count functions per file
uv run codecarto repo graph . -o json | jq '[.nodes[] | select(.type == "Function")] | length'
```
