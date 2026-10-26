"""
Codecarto CLI - Development and utility commands.

Usage:
    codecarto dev         # Start full dev loop (backend + frontend)
    codecarto serve       # Start backend API only
    codecarto web         # Start frontend only
    codecarto parse FILE  # Parse a Python file and display graph info
    codecarto info        # Show project info and environment
"""
import click
import subprocess
import sys
import os
from pathlib import Path


# THE CODE MAPS ANSWER ON E. Three services on one machine, three constants a
# person can recall without looking: 3141 the harness (qmcp), 1618 the panel
# (dossier), 2718 here. `e` is the base of natural growth, which is the shape
# this tool is for -- it exists because complexity grows faster than anybody
# can hold in their head.
#
# NOT 8000, WHICH THIS USED AND HALF THE PYTHON WORLD USES. A default that
# common is a default that collides, and the pair already lost a week to a port
# disagreement: the panel looked on 8000 while the harness served 3333, and
# reported an absent archive while the harness was answering.
#
# Override with `CODECARTO_PORT`, or `--port` on any command that binds one.
DEFAULT_PORT = 2718


def _default_port() -> int:
    """The port, from the environment or the constant.

    A callable rather than a literal default, so `CODECARTO_PORT` is read when
    the command runs rather than when this module is imported -- which is what
    lets a test set it and a shell export it.
    """
    import os

    raw = os.environ.get("CODECARTO_PORT", "")
    try:
        return int(raw) if raw else DEFAULT_PORT
    except ValueError:
        return DEFAULT_PORT


# Ensure stdout/stderr can handle Unicode on Windows (cp1252 can't encode emojis)
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Get repo root relative to this file
REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"


def get_repo_root() -> Path:
    """Return the repository root directory."""
    return REPO_ROOT


def _fail(message: str) -> None:
    """Say what failed, on stderr, and exit 1."""
    click.secho(f"✗ {message}", fg="red", err=True)
    raise SystemExit(1)


def _ensure_npm_dependencies() -> bool:
    """Ensure npm dependencies are installed. Returns True if successful."""
    node_modules = WEB_DIR / "node_modules"
    if not node_modules.is_dir():
        click.secho("  → Installing frontend dependencies (npm install)...", fg="yellow")
        try:
            result = subprocess.run(
                ["npm", "install"], 
                cwd=WEB_DIR, 
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.secho(f"  ✗ npm install failed: {result.stderr}", fg="red", err=True)
                return False
            click.secho("  ✓ Dependencies installed", fg="green")
        except FileNotFoundError:
            click.secho("  ✗ npm not found in PATH", fg="red", err=True)
            return False
    return True


@click.group()
@click.version_option(version="0.3.0", prog_name="codecarto")
def cli():
    """
    Codecarto CLI - Development utilities for source code visualization.

    \b
    Quick start:
        codecarto dev     Start full development environment
        codecarto serve   Start API server only
        codecarto info    Show environment info
    """
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Backend host address")
@click.option("--port", default=lambda: _default_port(),
              help=f"Backend port (default {DEFAULT_PORT}, or $CODECARTO_PORT)")
@click.option("--no-frontend", is_flag=True, help="Skip starting frontend")
def dev(host: str, port: int, no_frontend: bool):
    """
    Start the development loop (backend + frontend).

    \b
    Starts:
    - Uvicorn backend with hot reload on http://127.0.0.1:2718
    - Vite frontend on http://localhost:1234

    Press Ctrl+C to stop both servers.
    """
    click.secho("🚀 Starting Codecarto development environment...", fg="green", bold=True)
    
    # Start backend with .venv excluded from watch
    click.echo(f"  → Backend: http://{host}:{port}")
    backend_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "codecarto.main:app", 
        "--reload",
        "--reload-exclude", ".venv",
        "--reload-exclude", "node_modules",
        "--reload-exclude", "__pycache__",
        "--reload-exclude", "*.pyc",
        "--host", host,
        "--port", str(port)
    ])
    
    frontend_proc = None
    if not no_frontend:
        # Start frontend
        if not WEB_DIR.is_dir():
            backend_proc.terminate()
            _fail(f"Web directory not found at {WEB_DIR}")

        # Check if node_modules exists, if not run npm install
        if not _ensure_npm_dependencies():
            backend_proc.terminate()
            raise SystemExit(1)

        click.echo("  → Frontend: http://localhost:1234")
        try:
            frontend_proc = subprocess.Popen(
                ["npm", "run", "dev"], 
                cwd=WEB_DIR, 
                shell=True
            )
        except FileNotFoundError:
            backend_proc.terminate()
            _fail("npm not found in PATH")

    click.echo()
    click.secho("Press Ctrl+C to stop", fg="yellow")
    
    try:
        backend_proc.wait()
        if frontend_proc:
            frontend_proc.wait()
    except KeyboardInterrupt:
        click.echo()
        click.secho("Shutting down...", fg="yellow")
        backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()
        click.secho("✓ Stopped", fg="green")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host address")
@click.option("--port", default=lambda: _default_port(),
              help=f"Port number (default {DEFAULT_PORT}, or $CODECARTO_PORT)")
@click.option("--reload/--no-reload", default=True, help="Enable hot reload")
def serve(host: str, port: int, reload: bool):
    """
    Start the FastAPI backend server only.

    The running server's /docs lists the routes in its OpenAPI schema. The
    WebSockets and the routes kept out of the schema -- /app, /db/ and the
    PAM page's /pam/api/* -- are not there; docs/api.md names every one.
    """
    click.secho(f"🌐 Starting Codecarto API server...", fg="green", bold=True)
    click.echo(f"  → http://{host}:{port}")
    click.echo(f"  → Docs: http://{host}:{port}/docs")
    click.echo()
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "codecarto.main:app",
        "--host", host,
        "--port", str(port)
    ]
    if reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.secho("✓ Server stopped", fg="green")


@cli.command()
def web():
    """
    Start the frontend development server only.

    Runs 'npm run dev' in the web directory.
    Frontend will be available at http://localhost:1234
    """
    if not WEB_DIR.is_dir():
        _fail(f"Web directory not found at {WEB_DIR}")

    click.secho("🌍 Starting frontend dev server...", fg="green", bold=True)

    # Check if node_modules exists, if not run npm install
    if not _ensure_npm_dependencies():
        raise SystemExit(1)

    click.echo("  → http://localhost:1234")
    click.echo()
    
    try:
        subprocess.run(["npm", "run", "dev"], cwd=WEB_DIR, shell=True)
    except KeyboardInterrupt:
        click.secho("✓ Frontend stopped", fg="green")
    except FileNotFoundError:
        _fail("npm not found in PATH")


@cli.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Choice(["json", "text"]), default="text")
def parse(filepath: str, output: str):
    """
    Parse a Python file and display code structure.

    \b
    Example:
        codecarto parse myfile.py
        codecarto parse myfile.py -o json
    """
    from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST
    from codecarto.models.source_data import Folder, File
    import json
    
    # With -o json, stdout carries the JSON and nothing else.
    click.secho(f"📄 Parsing: {filepath}", fg="green", err=output == "json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        
        # Create file/folder structure for parser
        filename = Path(filepath).name
        file = File(name=filename, size=len(source), raw=source)
        folder = Folder(name="root", size=len(source), files=[file], folders=[])
        
        # Parse with AST parser
        parser = PythonCustomAST()
        graph = parser.parse(folder)
        
        nodes = list(graph.nodes(data=True))
        edges = list(graph.edges(data=True))
        
        if output == "json":
            result = {
                "nodes": [{"id": n[0], **n[1]} for n in nodes],
                "edges": [{"source": e[0], "target": e[1], **e[2]} for e in edges]
            }
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo()
            click.echo(f"  Nodes: {len(nodes)}")
            click.echo(f"  Edges: {len(edges)}")
            click.echo()
            
            # Show node types
            node_types = {}
            for node_id, node_data in nodes:
                ntype = node_data.get("type", "unknown")
                node_types[ntype] = node_types.get(ntype, 0) + 1
            
            if node_types:
                click.echo("  Node types:")
                for ntype, count in sorted(node_types.items()):
                    click.echo(f"    - {ntype}: {count}")
    except Exception as e:
        _fail(f"Parse error: {e}")


@cli.command()
def info():
    """
    Show project info and environment details.

    Displays Python version, package info, and configuration. Exits 1 when one
    of the package's dependencies it lists cannot be imported.
    """
    import platform
    
    click.secho("📦 Codecarto Project Info", fg="green", bold=True)
    click.echo()
    
    click.echo(f"  Python:     {platform.python_version()}")
    click.echo(f"  Platform:   {platform.system()} {platform.release()}")
    click.echo(f"  Repo root:  {REPO_ROOT}")
    click.echo()
    
    # Check for venv
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        click.echo(f"  Virtual env: {venv}")
    else:
        click.secho("  Virtual env: Not activated", fg="yellow")
    
    # Check for key dependencies
    click.echo()
    click.echo("  Dependencies:")
    # Each is in [project] dependencies, so one missing is a broken install.
    deps = ["fastapi", "networkx", "click", "gravis", "uvicorn"]
    missing = []
    for dep in deps:
        try:
            mod = __import__(dep)
            version = getattr(mod, "__version__", "installed")
            click.echo(f"    ✓ {dep}: {version}")
        except ImportError:
            missing.append(dep)
            click.secho(f"    ✗ {dep}: not found", fg="red")
    if missing:
        _fail(f"{', '.join(missing)} not installed; "
              "`uv sync --locked --extra dev --extra c-parsing` installs the environment")


@cli.command()
@click.option("--fix", is_flag=True, help="Auto-fix issues with ruff")
def lint(fix: bool):
    """
    Run ruff over the codecarto package.

    ruff is in the dev extra. Exits 1 when ruff finds issues or is missing.
    """
    import shutil

    click.secho("🔍 Running linter...", fg="green", bold=True)

    ruff = shutil.which("ruff")
    if ruff is None:
        _fail("ruff not found. `uv sync --locked --extra dev --extra c-parsing` installs it")
    cmd = [ruff, "check", str(REPO_ROOT / "codecarto")]
    if fix:
        cmd.append("--fix")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        _fail(f"ruff exited {result.returncode}")
    click.secho("✓ No issues found", fg="green")


@cli.command()
def docker():
    """
    Start Docker containers for development.

    Starts graphbase and codecarto containers using docker-compose.
    """
    click.secho("🐳 Starting Docker containers...", fg="green", bold=True)
    
    graphbase_compose = REPO_ROOT / "graphbase" / "docker-compose.yml"
    main_compose = REPO_ROOT / "docker-compose.yml"
    
    try:
        click.echo("  → Starting graphbase...")
        subprocess.run(
            ["docker-compose", "-f", str(graphbase_compose), "up", "--build", "-d"],
            check=True
        )
        
        click.echo("  → Starting codecarto...")
        subprocess.run(
            ["docker-compose", "-f", str(main_compose), "up", "--build", "-d"],
            check=True
        )
        
        click.secho("✓ Containers started", fg="green")
    except subprocess.CalledProcessError as e:
        _fail(f"Docker error: {e}")
    except FileNotFoundError:
        _fail("docker-compose not found in PATH")


@cli.command("docker-down")
def docker_down():
    """Stop and remove Docker containers."""
    click.secho("🐳 Stopping Docker containers...", fg="yellow", bold=True)
    
    graphbase_compose = REPO_ROOT / "graphbase" / "docker-compose.yml"
    main_compose = REPO_ROOT / "docker-compose.yml"
    
    try:
        subprocess.run(
            ["docker-compose", "-f", str(main_compose), "down", "-v"],
            check=True
        )
        subprocess.run(
            ["docker-compose", "-f", str(graphbase_compose), "down", "-v"],
            check=True
        )
        click.secho("✓ Containers stopped", fg="green")
    except subprocess.CalledProcessError as e:
        _fail(f"Docker error: {e}")
    except FileNotFoundError:
        _fail("docker-compose not found in PATH")


# ============================================================================
# Local Repository Commands
# ============================================================================

@cli.group()
def repo():
    """
    Local repository commands.
    
    \b
    Commands for working with local git repositories:
        codecarto repo scan PATH    Scan a local repo structure
        codecarto repo graph PATH   Generate a graph from local repo
        codecarto repo tree PATH    Display directory tree
    """
    pass


@repo.command("scan")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--ext", "-e", multiple=True, default=[".py"], help="File extensions to include")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def repo_scan(path: str, ext: tuple, output: str):
    """
    Scan a local repository and show structure.

    \b
    Examples:
        codecarto repo scan .
        codecarto repo scan /path/to/project
        codecarto repo scan . -e .py -e .js
        codecarto repo scan . -o json
    """
    from codecarto.services.local_repo_service import get_local_repo, get_file_stats
    import json
    
    extensions = list(ext) if ext else [".py"]
    
    # With -o json, stdout carries the JSON and nothing else.
    status = output == "json"
    click.secho(f"📂 Scanning: {Path(path).resolve()}", fg="green", err=status)
    click.echo(f"  Extensions: {', '.join(extensions)}", err=status)
    click.echo(err=status)

    try:
        directory = get_local_repo(path, extensions=extensions)
        stats = get_file_stats(directory)
        
        if output == "json":
            result = {
                "info": directory.info.model_dump(),
                "stats": stats,
                "structure": directory.root.model_dump()
            }
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo(f"  Repository: {directory.info.owner}/{directory.info.name}")
            click.echo(f"  Path: {directory.info.url}")
            click.echo()
            click.echo("  Statistics:")
            click.echo(f"    Total files: {stats['total_files']}")
            click.echo(f"    Python files: {stats['python_files']}")
            click.echo(f"    Folders: {stats['folders']}")
            click.echo(f"    Total size: {_format_size(stats['total_size'])}")
    except Exception as e:
        _fail(f"Scan error: {e}")


@repo.command("tree")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--ext", "-e", multiple=True, default=[".py"], help="File extensions to include")
@click.option("--depth", "-d", default=3, help="Maximum depth to display")
def repo_tree(path: str, ext: tuple, depth: int):
    """
    Display directory tree of a local repository.

    \b
    Examples:
        codecarto repo tree .
        codecarto repo tree /path/to/project -d 2
        codecarto repo tree . -e .py -e .js
    """
    from codecarto.services.local_repo_service import get_local_repo
    
    extensions = list(ext) if ext else [".py"]
    
    click.secho(f"🌳 Directory tree: {Path(path).resolve()}", fg="green")
    click.echo()
    
    try:
        directory = get_local_repo(path, extensions=extensions)
        _print_tree(directory.root, depth=depth)
    except Exception as e:
        _fail(f"Error: {e}")


@repo.command("graph")
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--ext", "-e", multiple=True, default=[".py"], help="File extensions to include")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
@click.option("--type", "-t", "graph_type", 
              type=click.Choice(["ast", "directory", "dependency"]), 
              default="ast",
              help="Type of graph to generate")
def repo_graph(path: str, ext: tuple, output: str, graph_type: str):
    """
    Generate a graph from a local repository.

    \b
    Graph types:
        ast        - Symbols (classes/functions/imports) + resolved
                     file-to-file dependency edges (default)
        directory  - Directory structure graph only
        dependency - Same output as 'ast' — the unified pipeline always
                     resolves dependency edges alongside symbols at this
                     depth, there's no separate deps-only view

    \b
    Examples:
        codecarto repo graph .
        codecarto repo graph /path/to/project -t dependency
        codecarto repo graph . -o json
    """
    from codecarto.services.local_repo_service import get_local_repo
    from codecarto.services.unified_parser_service import UnifiedParserService
    import json

    extensions = list(ext) if ext else [".py"]

    # With -o json, stdout carries the JSON and nothing else.
    status = output == "json"
    click.secho(f"📊 Generating {graph_type} graph: {Path(path).resolve()}", fg="green",
                err=status)
    click.echo(err=status)

    try:
        directory = get_local_repo(path, extensions=extensions)

        # "ast" and "dependency" both resolve to depth=2 — the unified
        # pipeline emits symbols AND resolved file-to-file dependency edges
        # together at that depth (see build_graph's
        # _add_python_dependency_edges), there's no separate symbols-only
        # vs deps-only mode. "directory" stays depth=1 (folders/files only).
        depth = 1 if graph_type == "directory" else 2
        graph = UnifiedParserService.build_graph(directory, depth, extensions)
        graph.name = directory.info.name

        nodes = list(graph.nodes(data=True))
        edges = list(graph.edges(data=True))
        
        if output == "json":
            result = {
                "name": graph.name,
                "type": graph_type,
                "nodes": [{"id": n[0], **n[1]} for n in nodes],
                "edges": [{"source": e[0], "target": e[1], **e[2]} for e in edges]
            }
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo(f"  Graph: {graph.name}")
            click.echo(f"  Type: {graph_type}")
            click.echo(f"  Nodes: {len(nodes)}")
            click.echo(f"  Edges: {len(edges)}")
            click.echo()
            
            # Show node type breakdown
            node_types = {}
            for node_id, node_data in nodes:
                ntype = node_data.get("kind", "unknown")
                node_types[ntype] = node_types.get(ntype, 0) + 1
            
            if node_types:
                click.echo("  Node types:")
                for ntype, count in sorted(node_types.items(), key=lambda x: -x[1])[:10]:
                    click.echo(f"    - {ntype}: {count}")
                if len(node_types) > 10:
                    click.echo(f"    ... and {len(node_types) - 10} more types")
    except Exception as e:
        import traceback
        if os.environ.get("DEBUG"):
            traceback.print_exc()
        _fail(f"Graph error: {e}")


@cli.group()
def cargo():
    """
    Cargo workspaces: read one, or record what cargo says about it.

    \b
        codecarto cargo read PATH     What the window will draw (runs nothing)
        codecarto cargo record PATH   Run cargo, write target/codecarto/
    """
    pass


@cargo.command("read")
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--json", "as_json", is_flag=True, help="Print the reading as JSON")
def cargo_read(path: str, as_json: bool):
    """
    Print what the /cargo routes would draw for PATH. Runs nothing.
    """
    import json

    from codecarto.services import cargo_service

    try:
        reading = cargo_service.read(path)
    except Exception as error:  # a reader that raised is a sentence here, never a traceback
        click.secho(f"✗ reading {path} stopped on something the reader did not expect: {error}", fg="red")
        raise SystemExit(1)
    if not reading.ok:
        click.secho(f"✗ {reading.reason}", fg="red")
        raise SystemExit(1)
    if as_json:
        click.echo(json.dumps(cargo_service.as_data(reading), indent=2, default=str))
        return
    click.secho(f"📦 {Path(path).resolve()} — read from {reading.engine}", fg="green")
    for package in reading.packages:
        if not package.member:
            continue
        extras = [x for x in (package.no_std and f"no_std {package.no_std}",
                              package.links and f"links {package.links}") if x]
        click.echo(f"  {package.name} {package.version}"
                   + (f"  [{', '.join(extras)}]" if extras else ""))
        for dep in package.dependencies:
            click.echo(f"    → {dep.name} {dep.version or dep.req}  ({dep.kind}"
                       + (", optional" if dep.optional else "")
                       + (f", {dep.platform}" if dep.platform else "") + ")")
    for doc in reading.documents:
        state = ("used" if doc.used else "not used") if doc.present else "absent"
        click.echo(f"  {doc.name}: {state}" + (f" — {doc.problem}" if doc.problem else ""))
    counts = {}
    for d in reading.diagnostics:
        counts[d.level] = counts.get(d.level, 0) + 1
    if counts:
        click.echo("  diagnostics: " + ", ".join(f"{n} {level}" for level, n in sorted(counts.items())))
    click.echo()
    click.echo(f"  {cargo_service.caveat(reading)}")


@cargo.command("record")
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--all-targets", is_flag=True,
              help="Check tests, examples and benches too (a no_std bin usually cannot build them)")
@click.option("--online", is_flag=True,
              help="Let cargo reach the network; by default it is run --offline")
@click.option("--map", "maps", multiple=True, metavar="BIN",
              help="Also link BIN and keep the linker's map as target/codecarto/BIN.map (repeatable)")
@click.option("--map-flag", default="-C link-arg=-Map={path}", show_default=True,
              help="How the linker is asked for the map; with a GCC linker, "
                   "'-C link-arg=-Wl,-Map={path}'")
@click.option("--profile", default="release", show_default=True,
              help="The profile a --map build uses: the one that is flashed")
@click.option("--timeout", default=600, show_default=True, help="Seconds each cargo command may take")
def cargo_record(path: str, all_targets: bool, online: bool, maps: tuple, map_flag: str,
                 profile: str, timeout: int):
    """
    Run cargo in PATH and write what it says to the workspace's target/codecarto/.

    \b
    This RUNS THE WORKSPACE'S CODE: `cargo check` compiles build scripts and
    proc macros and executes them. Run it on a workspace you would build. The
    window itself never runs cargo; it reads the files this writes:

    \b
        metadata.json   cargo metadata --format-version 1 --locked
        check.jsonl     cargo check --workspace --message-format=json --locked
        BIN.map         cargo rustc --locked --profile release --package PKG --bin BIN
                            -- -C link-arg=-Map=...   (PKG: the member with that bin)

    \b
    They go under the workspace root cargo names -- PATH's own, or the one
    above a member crate -- and nothing else is written: `--locked` keeps
    cargo from rewriting Cargo.lock.
    """
    import re
    import shlex
    import shutil

    from codecarto.services import cargo_service, link_map_service

    cargo_bin = shutil.which("cargo")
    if cargo_bin is None:
        click.secho("✗ cargo is not on PATH, so there is nothing to record. "
                    "Install a Rust toolchain (https://rustup.rs) and run this again; "
                    "the window still draws the manifests without it.", fg="red")
        raise SystemExit(1)

    root = Path(path).resolve()
    if not (root / "Cargo.toml").is_file():
        click.secho(f"✗ no Cargo.toml in {root}, so there is no workspace to record and "
                    f"nothing was run. Name a workspace root or a crate as PATH.", fg="red")
        raise SystemExit(1)
    out = root / cargo_service.DOCUMENTS
    offline = [] if online else ["--offline"]
    # (document, command, whether the document is the command's own output).
    # A map's command names the file the linker writes, which is known once
    # cargo metadata has said where the workspace's documents go.
    steps = [
        (cargo_service.METADATA_DOCUMENT,
         [cargo_bin, "metadata", "--format-version", "1", "--locked", *offline], True),
        (cargo_service.CHECK_DOCUMENT,
         [cargo_bin, "check", "--workspace", "--message-format=json", "--locked", *offline,
          *(["--all-targets"] if all_targets else [])], True),
        *((f"{binary}.map", None, False) for binary in maps),
    ]

    def package_of(binary: str) -> str | None:
        """The workspace package that owns a binary, from the metadata just
        recorded: `cargo rustc` in a workspace with no root package will not
        guess it."""
        import json

        try:
            data = json.loads((out / cargo_service.METADATA_DOCUMENT).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        members = set(data.get("workspace_members") or [])
        for package in data.get("packages") or []:
            if package.get("id") in members and any(
                    t.get("name") == binary and "bin" in (t.get("kind") or [])
                    for t in package.get("targets") or []):
                return package.get("name")
        return None

    failed = False
    metadata_failed = ""  # how the metadata step failed, when it did
    for name, command, captured in steps:
        if command is None:
            binary = name[: -len(".map")]
            package = package_of(binary)
            if package is None:
                failed = True
                if metadata_failed:
                    # The package is read from that step's document: say why it is not known.
                    click.secho(f"✗ cannot link {binary}: the metadata step {metadata_failed}, so "
                                f"which workspace member has that binary is not known", fg="red")
                else:
                    click.secho(f"✗ no workspace package has a binary named {binary}, "
                                f"by the {cargo_service.METADATA_DOCUMENT} just recorded", fg="red")
                continue
            # The linker writes the map itself; cargo's output is not the
            # document. The flag is split before the path goes in, so a path
            # with a space stays one argument.
            command = [cargo_bin, "rustc", "--locked", "--profile", profile, "--package", package,
                       "--bin", binary, *offline, "--",
                       *(part.format(path=(out / name).as_posix()) for part in shlex.split(map_flag))]
        click.secho(f"→ cargo {' '.join(command[1:])}", fg="cyan")
        before = (out / name).stat().st_mtime if (out / name).is_file() else None
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                    timeout=timeout, encoding="utf-8", errors="replace")
            stdout, stderr, code = result.stdout, result.stderr or "", result.returncode
        except subprocess.TimeoutExpired as expired:
            # A bound that fires is reported: what arrived is kept, and said to be partial.
            stdout = (expired.stdout or b"").decode("utf-8", "replace") \
                if isinstance(expired.stdout, bytes) else (expired.stdout or "")
            stderr, code = "", None
        if name == cargo_service.METADATA_DOCUMENT:
            if code != 0:
                metadata_failed = f"did not finish in {timeout}s" if code is None else f"exited {code}"
            out = _workspace_documents(stdout, root, cargo_service.DOCUMENTS)
            if out.parent.parent != root:
                click.echo(f"  cargo answered for the workspace at {out.parent.parent}; "
                           f"what is recorded goes there, where reading it looks")
        out.mkdir(parents=True, exist_ok=True)
        if captured:
            (out / name).write_text(stdout, encoding="utf-8")
        written = (out / name).as_posix() if out.parent.parent != root \
            else (out / name).relative_to(root).as_posix()
        if code is None:
            failed = True
            click.secho(f"  ✗ did not finish in {timeout}s"
                        + (f"; {name} holds only what arrived" if captured else ""), fg="red")
        elif code != 0 and name != cargo_service.CHECK_DOCUMENT:
            failed = True
            click.secho(f"  ✗ exited {code}: {_cargo_said(stderr)}", fg="red")
        elif name == cargo_service.CHECK_DOCUMENT and not _check_finished(stdout):
            # Stopped before compiling -- a dependency it could not fetch, a
            # lockfile `--locked` would not let it write: no diagnostics here
            # is not a clean build, and the reader says so too.
            failed = True
            click.secho(f"  ✗ cargo stopped before checking anything (exited {code}): "
                        f"{_cargo_said(stderr)}", fg="red")
        elif not captured and _unchanged(out / name, before):
            # cargo links only a binary that is out of date, and says
            # `Compiling` when it does; a build already current writes no map.
            failed = True
            if not re.search(r"^\s*Compiling\s", stderr, re.MULTILINE):
                recorded, seconds = link_map_service.age(out / name) if before is not None else ("", 0)
                old = (f"{name} is still the link of {recorded}, {seconds / 3600:.1f} h ago"
                       if before is not None else f"there is no {name}")
                click.secho(f"  ✗ cargo found the build up to date and did not relink, so the "
                            f"linker wrote nothing: {old}. It relinks once a source changes, or "
                            f"after `cargo clean --profile {profile}`.", fg="red")
            else:
                click.secho(f"  ✗ the build linked and the linker wrote no {name}; "
                            f"try --map-flag for this linker", fg="red")
        else:
            # A failing check still wrote its diagnostics, which is what it is for.
            click.secho(f"  ✓ wrote {written}" + (f" (cargo exited {code})" if code else ""), fg="green")
        if code and "--locked" in stderr:
            click.echo("  Cargo.lock is missing or out of date, and record does not rewrite it: "
                       "run `cargo generate-lockfile` or `cargo update` yourself, then record again.")
    if failed:
        raise SystemExit(1)


def _unchanged(path: Path, before: float | None) -> bool:
    """Whether the file at *path* is as it was before a command ran: still
    absent, or not written since."""
    if not path.is_file():
        return True
    return before is not None and path.stat().st_mtime == before


def _workspace_documents(metadata: str, root: Path, documents: Path) -> Path:
    """Where the window looks for what cargo said about PATH: the
    target/codecarto/ of the workspace root cargo names, which is above PATH
    when PATH is a member crate; PATH's own when cargo named none."""
    import json

    try:
        found = json.loads(metadata).get("workspace_root")
    except (ValueError, AttributeError):
        found = None
    return (Path(found).resolve() if found else root) / documents


def _check_finished(stdout: str) -> bool:
    """Whether cargo got as far as reporting the check's outcome."""
    import json

    for line in stdout.splitlines():
        if line.startswith("{") and "build-finished" in line:
            try:
                if json.loads(line).get("reason") == "build-finished":
                    return True
            except ValueError:
                continue
    return False


def _cargo_said(stderr: str) -> str:
    """cargo's first error line, or its last line."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return next((line for line in lines if line.startswith("error")), lines[-1] if lines else "")


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _print_tree(folder, prefix: str = "", depth: int = 3, current_depth: int = 0):
    """Print a directory tree."""
    from codecarto.models.source_data import Folder
    
    if current_depth >= depth:
        if folder.folders:
            click.echo(f"{prefix}└── ...")
        return
    
    # Print files
    items = folder.files + folder.folders
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        
        if isinstance(item, Folder):
            click.secho(f"{prefix}{connector}{item.name}/", fg="blue")
            new_prefix = prefix + ("    " if is_last else "│   ")
            _print_tree(item, new_prefix, depth, current_depth + 1)
        else:
            size = _format_size(item.size)
            click.echo(f"{prefix}{connector}{item.name} ({size})")


# ============================================================================
# Showgraph Commands
# ============================================================================

@cli.group()
def show():
    """
    The triplet's graph leg: every family and project the corpus names.

    \b
        codecarto show export --corpus ../qm --out ../qm/docs/show
    """
    pass


@show.command("export")
@click.option("--corpus", type=click.Path(exists=True, file_okay=False), required=True,
              help="A checkout of the governance corpus, whose families.json names the subjects")
@click.option("--subject", default="all", show_default=True,
              help="all, or index, family:<name> and project:<name>, comma-separated")
@click.option("--out", type=click.Path(file_okay=False), required=True,
              help="Where each subject's folder is written")
def show_export(corpus: str, subject: str, out: str):
    """
    Draw each subject's showgraph in the window, and write its pictures and show document.

    \b
    Each subject gets a folder under OUT -- index/, family/<name>/,
    project/<name>/ -- holding show.json and a picture of each view the
    window draws: estate.svg, code.svg and system.png. A view it cannot draw
    is stated in show.json with the reason. The pictures come from the real
    renderer, run headlessly by web/playwright.export.config.ts; a document
    naming a place on this machine fails the export.
    """
    import json
    import tempfile

    from codecarto.services import show_export as exporter, show_service

    corpus_path = Path(corpus).resolve()
    reading = show_service.read(corpus_path)
    if not reading.ok:
        _fail(reading.reason)
    try:
        chosen = exporter.subjects(reading, subject)
        identity = exporter.corpus_identity(corpus_path)
    except (ValueError, subprocess.CalledProcessError) as error:
        _fail(str(error))
    out_path = Path(out).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    sources = {}
    for s in chosen:
        if s.kind == "project" and reading.org and s.name in reading.inventory:
            sources[s.name] = {"repo": f"{reading.org}/{s.name}",
                               "commit": exporter.default_branch_head(reading.org, s.name)}
    plan = exporter.manifest(reading, chosen, out_path, identity, exporter.drawn_by(REPO_ROOT), sources)
    click.echo(f"Drawing {len(chosen)} subject(s) from {identity['repo']}@{identity['commit'][:7]}")

    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "manifest.json"
        manifest_path.write_text(json.dumps(plan), encoding="utf-8")
        env = {**os.environ, "SHOW_EXPORT_MANIFEST": str(manifest_path),
               "CODECARTO_CORPUS": str(corpus_path)}
        drawn = subprocess.run(["npx", "playwright", "test", "--config", "playwright.export.config.ts"],
                               cwd=WEB_DIR, env=env, shell=True)

    problems = []
    for s in chosen:
        document = out_path / s.folder / "show.json"
        if document.is_file():
            try:
                exporter.scrub(json.loads(document.read_text(encoding="utf-8")))
            except ValueError as error:
                problems.append(f"{s.folder}: {error}")
    problems += [f"{path} was not written" for path in exporter.missing(out_path, chosen)]
    if drawn.returncode or problems:
        for problem in problems:
            click.secho(f"  ✗ {problem}", fg="red", err=True)
        _fail(f"the export is not whole (the harness exited {drawn.returncode})")
    click.secho(f"✓ {len(chosen)} subject(s) written to {out}", fg="green")


if __name__ == "__main__":
    cli()