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

# Get repo root relative to this file
REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"


def get_repo_root() -> Path:
    """Return the repository root directory."""
    return REPO_ROOT


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
@click.option("--port", default=8000, help="Backend port")
@click.option("--no-frontend", is_flag=True, help="Skip starting frontend")
def dev(host: str, port: int, no_frontend: bool):
    """
    Start the development loop (backend + frontend).

    \b
    Starts:
    - Uvicorn backend with hot reload on http://127.0.0.1:8000
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
            click.secho(f"  ✗ Web directory not found at {WEB_DIR}", fg="red")
            backend_proc.terminate()
            return
        
        # Check if node_modules exists, if not run npm install
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
                    click.secho(f"  ✗ npm install failed: {result.stderr}", fg="red")
                    backend_proc.terminate()
                    return
                click.secho("  ✓ Dependencies installed", fg="green")
            except FileNotFoundError:
                click.secho("  ✗ npm not found in PATH", fg="red")
                backend_proc.terminate()
                return
        
        click.echo("  → Frontend: http://localhost:1234")
        try:
            frontend_proc = subprocess.Popen(
                ["npm", "run", "dev"], 
                cwd=WEB_DIR, 
                shell=True
            )
        except FileNotFoundError:
            click.secho("  ✗ npm not found in PATH", fg="red")
            backend_proc.terminate()
            return
    
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
@click.option("--port", default=8000, help="Port number")
@click.option("--reload/--no-reload", default=True, help="Enable hot reload")
def serve(host: str, port: int, reload: bool):
    """
    Start the FastAPI backend server only.

    \b
    API endpoints:
    - /palette   - Color palette management
    - /parser    - Source code parsing
    - /plotter   - Graph plotting
    - /polygraph - Graph operations
    - /repo      - GitHub repository reading
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
        click.secho(f"✗ Web directory not found at {WEB_DIR}", fg="red")
        return
    
    click.secho("🌍 Starting frontend dev server...", fg="green", bold=True)
    click.echo("  → http://localhost:1234")
    click.echo()
    
    try:
        subprocess.run(["npm", "run", "dev"], cwd=WEB_DIR, shell=True)
    except KeyboardInterrupt:
        click.secho("✓ Frontend stopped", fg="green")
    except FileNotFoundError:
        click.secho("✗ npm not found in PATH", fg="red")


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
    
    click.secho(f"📄 Parsing: {filepath}", fg="green")
    
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
        click.secho(f"✗ Parse error: {e}", fg="red")


@cli.command()
def info():
    """
    Show project info and environment details.

    Displays Python version, package info, and configuration.
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
    deps = ["fastapi", "networkx", "click", "gravis", "uvicorn"]
    for dep in deps:
        try:
            mod = __import__(dep)
            version = getattr(mod, "__version__", "installed")
            click.echo(f"    ✓ {dep}: {version}")
        except ImportError:
            click.secho(f"    ✗ {dep}: not found", fg="red")


@cli.command()
@click.option("--fix", is_flag=True, help="Auto-fix issues with ruff")
def lint(fix: bool):
    """
    Run linting on the codebase.

    Uses ruff for fast Python linting.
    """
    click.secho("🔍 Running linter...", fg="green", bold=True)
    
    cmd = ["ruff", "check", str(REPO_ROOT / "codecarto")]
    if fix:
        cmd.append("--fix")
    
    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            click.secho("✓ No issues found", fg="green")
    except FileNotFoundError:
        click.secho("✗ ruff not found. Install with: uv pip install ruff", fg="red")


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
        click.secho(f"✗ Docker error: {e}", fg="red")
    except FileNotFoundError:
        click.secho("✗ docker-compose not found in PATH", fg="red")


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
        click.secho(f"✗ Docker error: {e}", fg="red")
    except FileNotFoundError:
        click.secho("✗ docker-compose not found in PATH", fg="red")


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
    
    click.secho(f"📂 Scanning: {Path(path).resolve()}", fg="green")
    click.echo(f"  Extensions: {', '.join(extensions)}")
    click.echo()
    
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
        click.secho(f"✗ Scan error: {e}", fg="red")


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
        click.secho(f"✗ Error: {e}", fg="red")


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
        ast        - Parse Python AST for all files (default)
        directory  - Directory structure graph
        dependency - Import dependency graph

    \b
    Examples:
        codecarto repo graph .
        codecarto repo graph /path/to/project -t dependency
        codecarto repo graph . -o json
    """
    from codecarto.services.local_repo_service import get_local_repo
    from codecarto.services.parser_service import ParserService
    from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST
    import asyncio
    import json
    
    extensions = list(ext) if ext else [".py"]
    
    click.secho(f"📊 Generating {graph_type} graph: {Path(path).resolve()}", fg="green")
    click.echo()
    
    try:
        directory = get_local_repo(path, extensions=extensions)
        
        if graph_type == "ast":
            # Parse all files with AST
            parser = PythonCustomAST()
            graph = parser.parse(directory.root)
            graph.name = directory.info.name
        elif graph_type == "directory":
            # Use directory parser
            graph = asyncio.run(ParserService.parse_directory(directory))
        elif graph_type == "dependency":
            # Use dependency parser
            graph = asyncio.run(ParserService.parse_dependancy(directory))
        
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
                ntype = node_data.get("type", "unknown")
                node_types[ntype] = node_types.get(ntype, 0) + 1
            
            if node_types:
                click.echo("  Node types:")
                for ntype, count in sorted(node_types.items(), key=lambda x: -x[1])[:10]:
                    click.echo(f"    - {ntype}: {count}")
                if len(node_types) > 10:
                    click.echo(f"    ... and {len(node_types) - 10} more types")
    except Exception as e:
        click.secho(f"✗ Graph error: {e}", fg="red")
        import traceback
        if os.environ.get("DEBUG"):
            traceback.print_exc()


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


if __name__ == "__main__":
    cli()
