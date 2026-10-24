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
| `--port` | `codecarto.cli.DEFAULT_PORT`; `--help` prints it | Backend port; `CODECARTO_PORT` also sets it |
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

**Output:** Prints the backend, frontend and API-docs addresses as it starts
them.

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
| `--port` | `codecarto.cli.DEFAULT_PORT`; `--help` prints it | Port number; `CODECARTO_PORT` also sets it |
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
| `ast` | Folders, files, their symbols (classes, functions, imports), and the file-to-file dependency edges the pipeline resolves |
| `directory` | Folders and files only |
| `dependency` | The same graph as `ast`: the pipeline resolves dependency edges alongside symbols, and has no dependencies-only view |

**Examples:**

```bash
# AST graph (default)
uv run codecarto repo graph .

# Directory structure graph
uv run codecarto repo graph . -t directory

# The same graph as -t ast
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
    - import: 131
    - function: 64
    - class: 16
    - file: 12
    - external_module: 8
    - directory: 3
```

Each node's `kind` is what the text output counts, and what `-o json` carries
on every node: `directory`, `file`, `class`, `function`, `import` and
`external_module` for Python; each parser's own kinds for the other languages.

---

## Rust Workspace Commands

### `cargo`

Group command for Cargo workspaces. `read` only reads files. `record` runs
cargo, which executes the workspace's build scripts and proc macros, so run it
only on a workspace you would build.

| Command | Description |
|---------|-------------|
| `read` | Print what the `/cargo` routes would draw for a path |
| `record` | Run `cargo metadata` and `cargo check` in a path and write what they say to `target/codecarto/` |

### `cargo read`

```bash
uv run codecarto cargo read [PATH] [--json]
```

Prints which engine answered (`cargo metadata` when a recorded `metadata.json`
is newer than every manifest, `manifests` otherwise), each member crate and its
dependencies with their kind and condition, which recorded documents were found
and used, the diagnostics counts, and the caveat. `--json` prints the reading
`/cargo/data` serves. Exits 1, with the reason, when PATH holds no `Cargo.toml`.

### `cargo record`

```bash
uv run codecarto cargo record [PATH] [--all-targets] [--online] [--map BIN]... \
    [--map-flag TEXT] [--profile NAME] [--timeout SECONDS]
```

Runs, in PATH:

```bash
cargo metadata --format-version 1 --offline                 # -> target/codecarto/metadata.json
cargo check --workspace --message-format=json --offline     # -> target/codecarto/check.jsonl
# and, for each --map BIN, a link that keeps the linker's map:
cargo rustc --profile release --package PKG --bin BIN --offline -- -C link-arg=-Map=<PATH>/target/codecarto/BIN.map
```

A check that finds errors still writes its document -- recording the
diagnostics is the point -- and says cargo's exit status. `--all-targets` checks
tests, examples and benches too (a `no_std` binary usually cannot build them);
`--online` lets cargo reach the network; a command that outlives `--timeout`
(600s by default) keeps what arrived and says it is partial. Without cargo on
PATH it says so and exits 1; the window still draws the manifests. How the
window reads what this writes is in [Architecture](architecture.md#rust-cargo-and-the-firmware-languages).

`--map BIN` (repeatable) links a binary and keeps its map: the linker writes it,
so a build that finishes without one is a failure, not a document. `--map-flag`
is how the linker is asked -- the default suits `rust-lld`; a GCC linker wants
`'-C link-arg=-Wl,-Map={path}'`. `--profile` is the build measured, `release` by
default because that is the one flashed. `PKG` is the workspace member with a
binary named `BIN`, read from the `metadata.json` just recorded -- `cargo rustc`
will not guess it in a workspace with no root package -- and a `BIN` no member
has is said by name and fails the run.

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

Run `ruff check` over the `codecarto` package. ruff is in the `dev` extra
(`uv sync --extra dev`); without it the command says so and exits 1, and it
exits 1 when ruff finds issues.

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

A command that prints `✗` exits 1. With `-o json`, the status lines go to
stderr and stdout carries the JSON alone.

## Environment Variables

Every variable the code reads. `tests/test_docs_routes.py` fails when the code
reads one this table does not name, or this table names one nothing reads.

| Variable | Read by | Effect, and the value when unset |
|----------|---------|----------------------------------|
| `CODECARTO_PORT` | `dev`, `serve` | The backend port; `codecarto.cli.DEFAULT_PORT` |
| `CODECARTO_WEB_PORT` | `web/vite.config.js` | The frontend dev server's port; 1234 |
| `CODECARTO_WEB_HOST` | `web/vite.config.js` | The address the frontend dev server binds; `localhost` |
| `CODECARTO_API` | `web/vite.config.js` | The backend the dev server proxies API paths to; `codecarto.cli.DEFAULT_PORT` on 127.0.0.1 |
| `CODECARTO_FORGE` | `/topology` | The forge a topology box's repository link points at; `https://github.com` |
| `CODECARTO_CORPUS` | `/capabilities`, `/estate` | The governance corpus checkout read in place of the pin; the `governance/qm` submodule |
| `CODECARTO_REPO_ROOTS` | `/system` | Directories searched for a named repository, separated by the OS path separator; the checkout's parent and grandparent |
| `CC_CACHE_TTL` | the caches | Seconds a cached repository tree, parsed graph or extracted C source stays fresh; 86400 |
| `CC_GITHUB_TOKEN` | GitHub reads | A GitHub token, read first; the full order is in `docs/services.md`, *GitHub Token* |
| `GITHUB_TOKEN` | GitHub reads | A GitHub token, read after `gh auth token` |
| `GH_TOKEN` | GitHub reads | Read when `GITHUB_TOKEN` is unset |
| `MONGODB_URI` | `/db`, the caches | Mounts the graphbase routes under `/db` and adds MongoDB behind the cache; both off |
| `QMCP_URL` | `/topology`, `/estate` | Where the harness (qmcp) answers; `http://127.0.0.1:3141` |
| `LOOKSATWORDS_URL` | `/estate` | Where looksatwords answers; `http://127.0.0.1:1414` |
| `DOSSIER_OVERVIEW_SEAM` | `/overview`, `/estate` | The overview seam file read when a request names none; `overview.json` in the working directory |
| `PAM_LOG_FILE` | `/pam` | The log the PAM monitor tails; the first readable of `/var/log/auth.log`, `secure`, `messages`, `syslog` |
| `PAM_USE_JOURNALD` | `/pam` | `1`, `true` or `yes` reads PAM events from journald instead of a file |
| `DEBUG` | `repo graph` | Any value prints the traceback when the graph fails |
| `VIRTUAL_ENV` | `info` | Shown as the active virtual environment; set by activating one |

## Tips

### Running Without `uv run`

If you have the virtual environment activated:
```bash
source .venv/bin/activate  # or .venv\Scripts\activate
codecarto --help
```

### Piping JSON Output

With `-o json`, stdout is the JSON alone, so it pipes.

```bash
# The scan's statistics
uv run codecarto repo scan . -o json | jq '.stats'

# Save to file
uv run codecarto repo graph . -o json > graph.json

# Every file over 10 KB, at any depth
uv run codecarto repo scan . -o json | jq '.. | objects | select(has("raw") and .size > 10000) | .url'

# Count the functions
uv run codecarto repo graph . -o json | jq '[.nodes[] | select(.kind == "function")] | length'
```
