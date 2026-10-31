"""What the corpus's projects import, read from their own source: the modules
two or more of them share, and the imports that land in another project.

A code map holds what its repository holds, so a module a file imports from
elsewhere is left out of it (`stream_floor`), and nothing drawn said which
projects lean on the same libraries, or on each other's code. This reads each
project's own imports at one commit and sets them side by side.

**A NAME IS ALL AN IMPORT SAYS.** `import otto` names a module, not a
repository. It lands in another project only where that project's tree holds
a package of that name -- a folder with an `__init__.py`, at its root or under
`src/`, or a `package.json` naming it -- and no other project's tree does. A
module that is one file is not a package another project installs. Matched by
name alone across the corpus, eight imports landed in another project, and the
three that were wrong each named a single file at the other's root -- joe's
`cli.py`, ira's `osc.py`, carlos's `src/interop.py` -- where the importer
meant its own: qm's `ci/cli.py` and `ci/interop.py`, cesar's `Cesar/osc.py`.

**WHAT A PROJECT HOLDS IS ITS OWN.** Every top-level folder and module, at its
root or under `src/`, and every module in a folder that is no package, which
only a script that puts the folder on its path can import. A module inside a
package is the package's: TheatreMix's own `src/theatremix/showrunner.py` is
`theatremix.showrunner`, and its `import showrunner` is ShowRunner's.

**A MODULE NO PROJECT HOLDS IS SHARED WHEN TWO OR MORE IMPORT IT**: fastapi,
mithril. One that a single project imports is that project's own business, and
its code map's.

**ONE TREE, TWO GIT CALLS**, read at a commit and kept per commit, as the
manifests are (`show_service._manifests`): the tree listed with each file's
size, then every source file in one `git cat-file --batch`.

WHAT THIS CANNOT SEE. An import made at run time (`importlib`, an `import()` of
a computed name), a path a bundler aliases, a package installed under a name
other than the folder it is built from. Python, JavaScript and TypeScript
only: Rust's crates, C's headers and the languages read by pattern are not
read yet.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from codecarto.services import clones

PYTHON, SCRIPT = "python", "javascript"
LANGUAGES = (PYTHON, SCRIPT)
SCRIPT_FILES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".cts", ".mts")

# What two or more projects import before a page across projects draws it.
SHARED = 2

# Folders of what was installed or built, not written: a bundle's imports are
# its dependencies' too.
SKIPPED = re.compile(r"(?:^|/)(?:node_modules|dist|build|vendor|\.venv|venv|site-packages)/")
# A source file larger than this is generated.
LARGEST = 1 << 20

PYTHON_STDLIB = frozenset(sys.stdlib_module_names) | {"__future__"}
NODE_BUILTINS = frozenset({
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console", "crypto", "dgram",
    "dns", "events", "fs", "http", "http2", "https", "inspector", "module", "net", "os", "path",
    "perf_hooks", "process", "querystring", "readline", "stream", "string_decoder", "timers",
    "tls", "tty", "url", "util", "v8", "vm", "worker_threads", "zlib"})

# `from 'x'`, `import 'x'`, `import('x')`, `require('x')`: the quoted name after one.
SPECIFIER = re.compile(r"""(?:\bfrom|\bimport|\brequire)\s*\(?\s*(['"])([^'"\n]+)\1""")
# A package's name: `mithril`, `@playwright/test`. `Array.from(', ')` names none.
PACKAGE = re.compile(r"^(?:@[A-Za-z0-9][\w.-]*/)?[A-Za-z0-9][\w.-]*$")


def _git(repo: Path, *args: str, data: bytes | None = None) -> bytes | None:
    """git's output, or None when it could not answer."""
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], input=data,
                              capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def package_of(specifier: str) -> str | None:
    """The package a script's import names, or None for a path, a URL or a
    builtin (`fs`, and `node:fs`, which no package's name can be)."""
    parts = specifier.split("/")
    name = "/".join(parts[:2]) if specifier.startswith("@") else parts[0]
    if not PACKAGE.match(name) or name in NODE_BUILTINS:
        return None
    return name


def script_imports(text: str) -> list[str]:
    """The packages a JavaScript or TypeScript file imports, once each per statement."""
    return [name for _, specifier in SPECIFIER.findall(text)
            if (name := package_of(specifier))]


def python_imports(text: str) -> list[str]:
    """The top-level modules a Python file imports, the standard library's left out."""
    from codecarto.services.parsers.python_language_parser import extract_python_imports

    # Another project's source, parsed and not run: its `"\w"` is its own business.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        modules = extract_python_imports(text)
    tops = (module.split(".", 1)[0] for module in modules)
    return [top for top in tops if top not in PYTHON_STDLIB]


def holdings(paths: Iterable[str], manifests: dict[str, str]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """What a tree holds: every name its own code answers to, and of those the
    packages another project could import. `manifests` is each `package.json`
    by its path."""
    paths = set(paths)
    own: dict[str, set[str]] = {PYTHON: set(), SCRIPT: set()}
    packages: dict[str, set[str]] = {PYTHON: set(), SCRIPT: set()}
    for path in paths:
        if not path.endswith(".py") or SKIPPED.search(path):
            continue
        under = "src/" if path.startswith("src/") else ""
        top = path[len(under):].split("/")
        folder, _, file = path.rpartition("/")
        own[PYTHON].add(top[0] if len(top) > 1 else top[0][:-3])
        if under:
            # `from src.app import ...`, from a checkout that runs in place.
            own[PYTHON].add("src")
        if folder and f"{folder}/__init__.py" not in paths:
            own[PYTHON].add(file[:-3])
        if len(top) > 1 and f"{under}{top[0]}/__init__.py" in paths:
            packages[PYTHON].add(top[0])
    for text in manifests.values():
        try:
            name = json.loads(text).get("name")
        except (ValueError, AttributeError):
            continue
        if isinstance(name, str) and PACKAGE.match(name):
            own[SCRIPT].add(name)
            packages[SCRIPT].add(name)
    return own, packages


def _blobs(repo: Path, wanted: list[tuple[str, str]]) -> dict[str, str] | None:
    """Each (sha, path)'s text, by path, from one `git cat-file --batch`."""
    out = _git(repo, "cat-file", "--batch", data="".join(f"{sha}\n" for sha, _ in wanted).encode())
    if out is None:
        return None
    found: dict[str, str] = {}
    at = 0
    for _, path in wanted:
        end = out.find(b"\n", at)
        if end < 0:
            break
        header = out[at:end].decode("utf-8", "replace").split()
        at = end + 1
        if len(header) == 3 and header[1] == "blob":
            size = int(header[2])
            found[path] = out[at:at + size].decode("utf-8", "replace")
            at += size + 1
    return found


def read_tree(repo: Path, commit: str) -> dict[str, Any] | None:
    """What the tree at `commit` holds and imports, or None when git could not read it.

    `imports` is each language's modules by how many files import each one;
    a project's own names are not among them.
    """
    listing = _git(repo, "ls-tree", "-r", "-l", "-z", "--full-tree", commit)
    if listing is None:
        return None
    paths: list[str] = []
    wanted: list[tuple[str, str]] = []
    for row in listing.split(b"\0"):
        if not row:
            continue
        meta, _, path_bytes = row.partition(b"\t")
        fields = meta.decode("ascii", "replace").split()
        if len(fields) != 4 or fields[1] != "blob":
            continue
        path = path_bytes.decode("utf-8", "replace")
        paths.append(path)
        if SKIPPED.search(path) or not fields[3].isdigit() or int(fields[3]) > LARGEST:
            continue
        if path.endswith((".py", *SCRIPT_FILES)) or path.rsplit("/", 1)[-1] == "package.json":
            wanted.append((fields[2], path))
    texts = _blobs(repo, wanted) if wanted else {}
    if texts is None:
        return None

    own, packages = holdings(paths, {p: t for p, t in texts.items() if p.endswith("package.json")})
    files: dict[str, dict[str, set[str]]] = {PYTHON: defaultdict(set), SCRIPT: defaultdict(set)}
    for path, text in texts.items():
        if path.endswith(".py"):
            language, found = PYTHON, python_imports(text)
        elif path.endswith(SCRIPT_FILES):
            language, found = SCRIPT, script_imports(text)
        else:
            continue
        for module in found:
            if module not in own[language]:
                files[language][module].add(path)
    return {
        "commit": commit,
        "packages": {language: sorted(names) for language, names in packages.items()},
        "imports": {language: {module: len(where) for module, where in sorted(found.items())}
                    for language, found in files.items()},
    }


_TREES_READ: dict[tuple[str, str], dict[str, Any]] = {}


def read(clone: Path, commit: str | None = None) -> dict[str, Any] | None:
    """`read_tree` at `commit`, or at the clone's default branch when none is
    given, kept per commit, as the manifests are. None when git could not read
    it -- a clone that lacks the commit, too -- which is kept for nothing: the
    next drawing asks again."""
    commit = commit or clones.default_commit(clone)
    if commit is None:
        return None
    key = (str(clone), commit)
    if key not in _TREES_READ:
        tree = read_tree(clone, commit)
        if tree is None:
            return None
        _TREES_READ[key] = tree
    return _TREES_READ[key]


def across(trees: dict[str, dict[str, Any]], among: Iterable[str] | None = None) -> dict[str, Any]:
    """Set the trees side by side.

    `trees` is every project read, by name: who holds a package is asked of
    all of them. `among` is the projects a page draws (every one, when None):
    their imports are the ones set out.

    - `links`: an import of a package one other project holds, one row per
      importer, holder and module, with the files that import it;
    - `shared`: a module no project holds that `SHARED` or more of `among`
      import, with each importer's files;
    - `ambiguous`: a package two or more projects hold that one of `among`
      imports, which is no link to either.
    """
    drawn = sorted(set(trees) if among is None else set(among) & set(trees), key=str.lower)
    holders: dict[tuple[str, str], set[str]] = defaultdict(set)
    for name, tree in trees.items():
        for language, names in tree["packages"].items():
            for module in names:
                holders[(language, module)].add(name)

    links: list[dict[str, Any]] = []
    ambiguous: dict[tuple[str, str], dict[str, Any]] = {}
    importers: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for name in drawn:
        for language, modules in trees[name]["imports"].items():
            for module, files in modules.items():
                held = holders.get((language, module), set()) - {name}
                if len(held) == 1:
                    links.append({"source": name, "target": next(iter(held)), "module": module,
                                  "language": language, "files": files})
                elif held:
                    row = ambiguous.setdefault((language, module), {
                        "module": module, "language": language,
                        "holders": sorted(held, key=str.lower), "importers": []})
                    row["importers"].append(name)
                else:
                    importers[(language, module)][name] = files
    shared = [{"module": module, "language": language, "projects": projects}
              for (language, module), projects in importers.items() if len(projects) >= SHARED]
    shared.sort(key=lambda row: (-len(row["projects"]), row["language"], row["module"]))
    return {
        "links": links,
        "shared": shared,
        "ambiguous": sorted(ambiguous.values(), key=lambda row: (row["language"], row["module"])),
        # The modules one project alone imports: counted, and drawn on no page across projects.
        "alone": sum(1 for projects in importers.values() if len(projects) < SHARED),
    }


def survey(clones_dir: Path, show: Path, back: int = 24) -> dict[str, Any]:
    """What `codecarto show imports` reports: the corpus's imports set side by
    side at the commits its code maps were drawn from, and at the end of each
    of the `back` months before, so the view's growth can be set beside the
    code's.

    `clones_dir` holds a clone of each project, `<project>.git` or `<project>`
    (bare clones do); a project with none, or whose clone lacks the commit its
    map was drawn from, is named and left out, as `show growth` leaves it.
    """
    from codecarto.services import show_growth as growing

    trees: dict[str, dict[str, Any]] = {}
    drawn: dict[str, tuple[Path, str]] = {}
    left_out: dict[str, str] = {}
    for document in sorted((show / "project").glob("*/show.json")):
        name = document.parent.name
        data = json.loads(document.read_text(encoding="utf-8"))
        commit = ((data.get("provenance") or {}).get("source") or {}).get("commit")
        repo = next((p for p in (clones_dir / f"{name}.git", clones_dir / name) if p.is_dir()), None)
        tree = read_tree(repo, commit) if commit and repo is not None else None
        if not commit:
            left_out[name] = "its document names no source commit"
        elif repo is None:
            left_out[name] = "no clone"
        elif tree is None:
            left_out[name] = f"its clone lacks {commit[:7]}"
        else:
            trees[name] = tree
            drawn[name] = (repo, commit)
    now = across(trees)

    stamps = [(_git(repo, "log", "-1", "--format=%cI", commit) or b"").decode().strip()[:7]
              for repo, commit in drawn.values()]
    through = max((s for s in stamps if s), default=None)
    rows: list[dict[str, Any]] = []
    if through:
        first = growing.months("2000-01", through)[-back:][0]
        read_at: dict[tuple[str, str], dict[str, Any] | None] = {}
        for month in growing.months(first, through):
            at: dict[str, dict[str, Any]] = {}
            for name, (repo, commit) in drawn.items():
                rev = (_git(repo, "rev-list", "-1", "--first-parent",
                            f"--before={growing.month_end(month)}", commit) or b"").decode().strip()
                if not rev:
                    continue
                if (name, rev) not in read_at:
                    read_at[(name, rev)] = read_tree(repo, rev)
                if read_at[(name, rev)] is not None:
                    at[name] = read_at[(name, rev)]
            then = across(at)
            rows.append({"month": month, "projects": len(at), "shared": len(then["shared"]),
                         "links": len(then["links"]),
                         "joins": len(then["links"]) + sum(len(r["projects"]) for r in then["shared"])})
    series = ("projects", "shared", "joins")
    return {
        "through": through,
        "projects": {name: {"commit": tree["commit"], "packages": tree["packages"],
                            "imports": sum(len(m) for m in tree["imports"].values())}
                     for name, tree in trees.items()},
        "left_out": left_out,
        **now,
        "months": rows,
        "doubling_months": {s: {str(span): growing.doubling([r[s] for r in rows], span)
                                for span in growing.SPANS} for s in series},
    }


def summary(report: dict[str, Any], top: int = 12) -> list[str]:
    """The links, the most shared modules, and how fast what a view draws grows."""
    lines = [f"{len(report['projects'])} projects read through {report['through']}"
             + (f"; left out: {', '.join(f'{n} ({why})' for n, why in report['left_out'].items())}"
                if report["left_out"] else "."), ""]
    lines.append(f"{len(report['links'])} import(s) of another project's package:")
    lines += [f"  {link['source']} -> {link['target']}  {link['language']}:{link['module']}  "
              f"{link['files']} file(s)" for link in report["links"]]
    for row in report["ambiguous"]:
        lines.append(f"  not a link: {row['language']}:{row['module']}, held by "
                     f"{', '.join(row['holders'])}, imported by {', '.join(row['importers'])}")
    joins = sum(len(r["projects"]) for r in report["shared"])
    lines += ["", f"{len(report['shared'])} module(s) two or more projects import, {joins} joins; "
                  f"{report['alone']} imported by one alone. The most shared:"]
    lines += [f"  {len(row['projects']):3d}  {row['language']}:{row['module']}" for row in report["shared"][:top]]
    lines += ["", "Months to double, fitted over the last 6, 12, 24 months:"]
    for name, spans in report["doubling_months"].items():
        said = ", ".join("not growing" if v is None else f"{v:.1f}" for v in spans.values())
        lines.append(f"  {name:10s} {said}")
    return lines
