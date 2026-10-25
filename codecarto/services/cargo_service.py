"""A Cargo workspace -- its crates, their targets, what each depends on, and
what the last build said about them -- as a graph this project already draws.

**THE WINDOW READS WHAT CARGO WROTE, AND NEVER RUNS CARGO.** Running `cargo` on
a path is running that path's code: a build script and a proc macro execute at
build time, and even `cargo metadata` asks the configured `rustc` -- which a
repository's own `.cargo/config.toml` may name, or wrap -- for target facts. A
route that ran it would execute whatever a cloned repository put there, for
anyone who can reach the port. So this module reads two things only:

- **the manifests**: every `Cargo.toml` under the path, its `Cargo.lock`, and
  `.cargo/config.toml` -- read as TOML, never interpreted;
- **the documents cargo wrote**: `target/codecarto/metadata.json` (the output
  of `cargo metadata --format-version 1`) and `target/codecarto/check.jsonl`
  (`cargo check --message-format=json`). A person writes them, deliberately,
  with `codecarto cargo record`, or their own build does; the window reads them
  as dossier's overview is read -- with its age beside it.

**WHICH ENGINE ANSWERED IS PART OF THE ANSWER.** A `metadata.json` newer than
every manifest is cargo's resolution and is used as it stands: resolved
features, dependency kinds, platform conditions, exact versions. Otherwise the
manifests are read directly and the caveat says what that cannot see --
features as declared rather than resolved, every platform's dependencies drawn
at once. A metadata document older than a manifest is *not* used, and the
reading says so: a stale resolution delivered as current is worse than a
declared one labelled as declared.

**AN ABSENT DOCUMENT IS A SENTENCE, NEVER AN EMPTY OVERLAY.** No `check.jsonl`
draws no diagnostics and says there was nothing to read, which is a different
sentence from "the last check was clean".

WHAT THIS CANNOT SEE. Whether the build would succeed now. A diagnostic is what
`rustc` said when the document was written; once a source or manifest changes
afterwards the document is stale, is not used, and nothing here re-checks.
"""

from __future__ import annotations

import glob
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOCUMENTS = Path("target") / "codecarto"
METADATA_DOCUMENT = "metadata.json"
CHECK_DOCUMENT = "check.jsonl"
RECORD_COMMAND = "uv run codecarto cargo record"

# Bounds on the walk. A bound that fires is reported in `notes`, never absorbed.
MAX_MANIFESTS = 400
MAX_DIAGNOSTICS = 2000
SKIP_DIRS = {"target", ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

DEP_KINDS = ("normal", "build", "dev")

# The span-less lines rustc ends a crate with -- a summary of its run, not a
# diagnostic of the code: counted, one error would read as two.
RUN_SUMMARY = re.compile(r"(aborting due to |\d+ warnings? emitted\b)")

# What each node is drawn as. This module decides the kinds; the looks are the
# construct vocabulary's where one applies (a native library is the FFI
# boundary, `linkage.foreign-block`; a memory map is `layout.region`).
LOOKS: dict[str, tuple[str, str]] = {
    "workspace": ("square", "#8b5cf6"),
    "crate": ("hexagon", "#f74c00"),
    "external_crate": ("circle", "#94a3b8"),
    "target": ("square", "#4a9eff"),
    "feature": ("triangle", "#22d3ee"),
    "native_lib": ("rectangle", "#f97316"),
    "device_target": ("triangle", "#ef4444"),
    "memory_map": ("square", "#d97706"),
}
TARGET_LOOKS: dict[str, tuple[str, str]] = {
    "lib": ("square", "#4a9eff"), "rlib": ("square", "#4a9eff"),
    "staticlib": ("square", "#6ab0e8"), "cdylib": ("square", "#6ab0e8"),
    "bin": ("diamond", "#ff9d3d"),
    "custom-build": ("triangle", "#eab308"),
    "proc-macro": ("hexagon", "#ec4899"),
    "test": ("circle", "#64748b"), "example": ("circle", "#64748b"),
    "bench": ("circle", "#64748b"),
}
EDGE_LOOKS: dict[str, dict[str, Any]] = {
    "normal": {"color": "#94a3b8", "size": 2},
    "build": {"color": "#eab308", "size": 2},
    "dev": {"color": "#64748b", "size": 1, "style": "dashed"},
}


# ── The reading ───────────────────────────────────────────────────────────────


@dataclass
class Target:
    name: str
    kinds: list[str]
    src: str = ""
    declared: bool = True


@dataclass
class Dependency:
    name: str
    """The package depended on."""
    kind: str = "normal"
    req: str = ""
    alias: str = ""
    optional: bool = False
    platform: str = ""
    source: str = "registry"
    path: str = ""
    version: str = ""
    """The locked or resolved version, when one is known."""


@dataclass
class Package:
    name: str
    version: str = ""
    manifest: str = ""
    edition: str = ""
    member: bool = True
    source: str = "local"
    links: str = ""
    no_std: str = ""
    targets: list[Target] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    features: dict[str, list[str]] = field(default_factory=dict)
    resolved_features: list[str] = field(default_factory=list)
    memory_maps: list[str] = field(default_factory=list)
    workspace: str = ""
    """The manifest of the workspace this package is a member of, if any."""


@dataclass
class Document:
    name: str
    path: str
    present: bool
    generated_at: str = ""
    age_seconds: float | None = None
    stale: bool = False
    used: bool = False
    problem: str = ""


@dataclass
class Diagnostic:
    level: str
    message: str
    package: str = ""
    target: str = ""
    code: str = ""
    file: str = ""
    line: int = 0
    kinds: list[str] = field(default_factory=list)
    """The target's kinds: a package's lib and bin share its name."""


@dataclass
class Reading:
    root: str
    packages: list[Package] = field(default_factory=list)
    workspaces: list[dict[str, Any]] = field(default_factory=list)
    engine: str = "manifests"
    documents: list[Document] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    scripts: list[dict[str, Any]] = field(default_factory=list)
    build_success: bool | None = None
    firmware: dict[str, Any] = field(default_factory=dict)
    lock: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    """Each package name's versions and what each depends on: the lockfile's,
    or cargo's resolution's when metadata.json answered."""
    notes: list[str] = field(default_factory=list)
    reason: str = ""
    newest_source: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.reason

    def package(self, name: str) -> Package | None:
        return next((p for p in self.packages if p.name == name), None)


def _toml():
    """tomllib (3.11+), or the tomli backport, or None."""
    try:
        import tomllib  # type: ignore[import-not-found]
        return tomllib
    except ModuleNotFoundError:
        try:
            import tomli  # type: ignore[import-not-found]
            return tomli
        except ModuleNotFoundError:
            return None


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def read(path: Path | str, documents: Path | str | None = None) -> Reading:
    """Everything this window can know about the Cargo workspace at *path*,
    without running anything. A path with no manifest is a reason, not an
    empty workspace."""
    root = Path(path)
    reading = Reading(root=str(root))
    if not root.is_dir():
        reading.reason = f"{root} is not a directory this server can read"
        return reading
    toml = _toml()
    if toml is None:
        reading.reason = ("reading Cargo.toml needs Python 3.11's tomllib or the "
                          "tomli package, and this interpreter has neither")
        return reading

    manifests: list[Path] = []
    memory_maps: list[Path] = []
    newest, newest_manifest = _walk(root, reading, manifests, memory_maps)
    if not manifests:
        reading.reason = (f"no Cargo.toml under {root.as_posix()} -- this is not a "
                          f"Cargo project, or its manifests sit inside a skipped "
                          f"directory ({', '.join(sorted(SKIP_DIRS))})")
        return reading

    parsed: dict[Path, dict] = {}
    _parse(manifests, parsed, reading, root, toml)
    # A member is read wherever it sits, even inside a directory the walk
    # skips (`build/`, `dist/`) -- and a member found there may name another.
    tried: set[Path] = set()  # a walk the manifest bound stopped is not retried
    while unwalked := [d for d in _unwalked_members(parsed, manifests, root) if d not in tried]:
        tried.update(unwalked)
        for directory in unwalked:
            start = len(manifests)
            sources, manifest_time = _walk(root / _rel(directory, root), reading, manifests, memory_maps)
            newest, newest_manifest = max(newest, sources), max(newest_manifest, manifest_time)
            _parse(manifests[start:], parsed, reading, root, toml)
    reading.newest_source = newest

    docs_dir = Path(documents) if documents else root / DOCUMENTS
    metadata_doc, metadata = _read_metadata(docs_dir, newest_manifest, root)
    reading.documents.append(metadata_doc)
    if metadata is not None:
        try:
            _from_metadata(reading, metadata, root)
            reading.engine = "cargo metadata"
        except Exception as error:
            # cargo's identity with entries cargo never writes is not cargo's
            # answer either: the same as a document of the wrong shape.
            reading.packages, reading.workspaces, reading.lock = [], [], {}
            metadata_doc.used = False
            metadata_doc.problem = (f"{METADATA_DOCUMENT} has `version: 1` and a `packages` list, but "
                                    f"entries of a shape cargo does not write ({type(error).__name__}: "
                                    f"{error}), so the manifests were read instead")
            metadata = None
    if metadata is None:
        _from_manifests(reading, parsed, root, toml)
    for package in reading.packages:
        if package.member and package.manifest:
            directory = (root / package.manifest).parent
            package.memory_maps = sorted(_rel(m, root) for m in memory_maps if m.parent == directory)
            package.no_std = _no_std(root, package)

    check_doc = _read_check(reading, docs_dir, root)
    reading.documents.append(check_doc)
    reading.firmware = _firmware(root, reading, memory_maps, toml)
    return reading


def _parse(manifests: list[Path], parsed: dict[Path, dict], reading: Reading, root: Path, toml) -> None:
    for manifest in manifests:
        try:
            parsed[manifest] = toml.loads(manifest.read_text(encoding="utf-8"))
        except Exception as error:  # a manifest that does not parse is reported
            reading.notes.append(f"{_rel(manifest, root)} did not parse: {error}")


def _unwalked_members(parsed: dict[Path, dict], manifests: list[Path], root: Path) -> list[Path]:
    """Members the walk did not reach: those a workspace names, and the path
    dependencies inside a workspace's directory, which cargo makes members."""
    walked = {m.parent.resolve() for m in manifests}
    workspaces: list[Path] = []
    found: set[Path] = set()
    for manifest, data in parsed.items():
        ws = data.get("workspace")
        if isinstance(ws, dict):
            workspaces.append(manifest.parent.resolve())
            try:
                found |= _member_dirs(manifest.parent, ws.get("members"))
            except Exception:
                pass  # `_from_manifests` notes the shape
    for manifest, data in parsed.items():
        for directory in _path_dependency_dirs(manifest, data):
            if any(_under(directory, w) for w in workspaces) and (directory / "Cargo.toml").is_file():
                found.add(directory)
    return sorted(d for d in found - walked if _under(d, root.resolve()))


def _path_dependency_dirs(manifest: Path, data: dict) -> list[Path]:
    """Every `path` a manifest's dependency tables name -- its own and its
    `[workspace.dependencies]` -- against its directory. One that inherits
    with `workspace = true` is named by the workspace's table instead."""
    try:
        tables = [table for _, _, table in _dependency_tables(data)]
        ws = data.get("workspace")
        if isinstance(ws, dict) and isinstance(ws.get("dependencies"), dict):
            tables.append(ws["dependencies"])
        return [(manifest.parent / str(spec["path"])).resolve()
                for table in tables for spec in table.values()
                if isinstance(spec, dict) and spec.get("path") and not spec.get("workspace")]
    except Exception:
        return []  # `_from_manifests` notes the shape


def _walk(top: Path, reading: Reading, manifests: list[Path],
          memory_maps: list[Path]) -> tuple[float, float]:
    """Every Cargo.toml and memory map under *top*, added to the lists; the
    newest mtime of any manifest or Rust source, which makes `check.jsonl`
    stale; and the newest of a manifest alone -- a Cargo.toml, a Cargo.lock or
    a `.cargo/config.toml` -- which makes `metadata.json` stale."""
    newest = newest_manifest = 0.0
    for directory, dirs, files in os.walk(top):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and (not d.startswith(".") or d == ".cargo"))
        here = Path(directory)
        for name in files:
            manifest = (name in ("Cargo.toml", "Cargo.lock")
                        or (here.name == ".cargo" and name in ("config.toml", "config")))
            if manifest or name.endswith(".rs"):
                try:
                    mtime = (here / name).stat().st_mtime
                except OSError:
                    mtime = 0.0
                newest = max(newest, mtime)
                if manifest:
                    newest_manifest = max(newest_manifest, mtime)
            if name == "Cargo.toml":
                if len(manifests) >= MAX_MANIFESTS:
                    if not any("manifest bound" in n for n in reading.notes):
                        reading.notes.append(
                            f"stopped at the manifest bound ({MAX_MANIFESTS}); "
                            f"packages past it are not drawn")
                    continue
                manifests.append(here / name)
            elif name == "memory.x" or name.endswith((".ld", ".lds")):
                memory_maps.append(here / name)
    return newest, newest_manifest


# ── From the manifests ────────────────────────────────────────────────────────


def _strings(value: Any, key: str) -> list[str]:
    """A manifest's list of strings, or the reason it is not one."""
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"`{key}` is {value!r}, not a list of strings")
    return value


def _table(value: Any, key: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"`{key}` is {value!r}, not a table")
    return value


def _member_dirs(directory: Path, patterns: Any) -> set[Path]:
    """The directories a `members` list names, expanded as cargo expands it:
    each entry joined to the workspace's directory -- so `"."` is the workspace
    itself and an absolute path is itself -- and globbed only when it holds a
    pattern. A directory without a Cargo.toml is not a member."""
    found = set()
    for pattern in _strings(patterns, "workspace.members"):
        if glob.has_magic(pattern):
            matches = glob.glob(os.path.normpath(os.path.join(glob.escape(str(directory)), pattern)))
        else:
            matches = [os.path.normpath(os.path.join(directory, pattern))]
        for match in matches:
            if (Path(match) / "Cargo.toml").is_file():
                found.add(Path(match).resolve())
    return found


def _under(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def _excluded(ws: dict, directory: Path) -> bool:
    """cargo's rule: under an `exclude` entry, and not under an entry `members`
    names without a pattern."""
    return (any(_under(directory, e) for e in ws["exclude"])
            and not any(_under(directory, m) for m in ws["explicit"]))


def _with_path_members(members: set[Path], ws: dict, parsed: dict[Path, dict], root: Path) -> set[Path]:
    """*members* and, as cargo adds them, every path dependency of a member
    that lies inside the workspace's directory -- so a root `[workspace]` with
    no `members` still has its path-dependency crates."""
    by_dir = {m.parent.resolve(): (m, d) for m, d in parsed.items()}
    queue = sorted(members)
    while queue:
        manifest, data = by_dir.get(queue.pop(), (None, None))
        if data is None or not isinstance(data.get("package"), dict):
            continue
        try:
            found = _dependencies(data, manifest.parent, ws, {}, root)
        except Exception:
            continue  # the package itself is noted when it is read
        for dep in found:
            target = (root / dep.path).resolve()
            if (dep.source == "path" and target not in members and target in by_dir
                    and _under(target, ws["directory"]) and not _excluded(ws, target)
                    and not isinstance(by_dir[target][1].get("workspace"), dict)):
                members.add(target)
                queue.append(target)
    return members


def _features(data: dict) -> dict[str, list[str]]:
    return {str(k): list(_strings(v, f"features.{k}"))
            for k, v in _table(data.get("features"), "features").items()}


def _from_manifests(reading: Reading, parsed: dict[Path, dict], root: Path, toml) -> None:
    """Every package the manifests declare. A manifest that is TOML but not of
    a manifest's shape -- a dependency that is `true`, a feature that is a
    number -- is a note naming it, and the rest of the workspace is still read."""
    workspaces: dict[Path, dict] = {}
    for manifest, data in parsed.items():
        ws = data.get("workspace")
        if isinstance(ws, dict):
            directory = manifest.parent
            try:
                patterns = _strings(ws.get("members"), "workspace.members")
                members = _member_dirs(directory, patterns)
                record = {"manifest": _rel(manifest, root),
                          "directory": directory.resolve(),
                          "exclude": [(directory / e).resolve()
                                      for e in _strings(ws.get("exclude"), "workspace.exclude")],
                          "explicit": [Path(os.path.normpath(os.path.join(directory, m))).resolve()
                                       for m in patterns if not glob.has_magic(m)],
                          "dependencies": _table(ws.get("dependencies"), "workspace.dependencies"),
                          "package": _table(ws.get("package"), "workspace.package")}
            except Exception as error:
                reading.notes.append(f"{_rel(manifest, root)}'s [workspace] has a shape this reader "
                                     f"does not take ({error}), so it claims no members")
                continue
            if isinstance(data.get("package"), dict):
                members.add(directory.resolve())
            record["members"] = _with_path_members(
                {m for m in members if not _excluded(record, m)}, record, parsed, root)
            workspaces[directory.resolve()] = record
            reading.workspaces.append({"manifest": _rel(manifest, root),
                                       "members": sorted(_rel(m, root) for m in record["members"])})

    def workspace_of(directory: Path) -> dict | None:
        for ws_dir, ws in workspaces.items():
            if directory.resolve() in ws["members"]:
                return ws
        return None

    def its_own(directory: Path) -> bool:
        """No workspace claims it as cargo looks upward for one: every
        workspace whose directory holds it excludes it, so it is a workspace of
        one -- a crate of this checkout, not something it depends on."""
        return all(_excluded(ws, directory.resolve()) for ws_dir, ws in workspaces.items()
                   if _under(directory.resolve(), ws_dir))

    by_dir: dict[Path, str] = {}
    for manifest, data in parsed.items():
        pkg = data.get("package")
        if isinstance(pkg, dict) and pkg.get("name"):
            by_dir[manifest.parent.resolve()] = str(pkg["name"])

    for manifest, data in sorted(parsed.items()):
        pkg = data.get("package")
        if not isinstance(pkg, dict) or not pkg.get("name"):
            continue
        directory = manifest.parent
        ws = workspace_of(directory)
        inherited = (ws or {}).get("package", {})

        def field_of(key: str) -> str:
            value = pkg.get(key, "")
            if isinstance(value, dict) and value.get("workspace"):
                value = inherited.get(key, "")
            return str(value or "")

        try:
            package = Package(
                name=str(pkg["name"]), version=field_of("version"), edition=field_of("edition"),
                manifest=_rel(manifest, root), links=str(pkg.get("links", "") or ""),
                member=bool(ws) or its_own(directory),
                features=_features(data),
                workspace=ws["manifest"] if ws else "",
            )
            package.targets = _targets(data, pkg, directory, root)
            package.dependencies = _dependencies(data, directory, ws, by_dir, root)
        except Exception as error:
            reading.notes.append(f"{_rel(manifest, root)} has a shape this reader does not take "
                                 f"({error}), so its package is not drawn")
            continue
        reading.packages.append(package)

    _apply_lock(reading, root)


def _targets(data: dict, pkg: dict, directory: Path, root: Path) -> list[Target]:
    """Declared targets, and the ones Cargo discovers by convention."""
    found: list[Target] = []
    crate = str(pkg["name"]).replace("-", "_")
    lib = data.get("lib") if isinstance(data.get("lib"), dict) else None
    if lib is not None or (directory / "src" / "lib.rs").is_file():
        lib = lib or {}
        kinds = ["proc-macro"] if lib.get("proc-macro") else list(lib.get("crate-type", ["lib"]))
        src = lib.get("path", "src/lib.rs")
        found.append(Target(str(lib.get("name", crate)), kinds, _rel(directory / src, root),
                            declared="lib" in data))
    sections = (("bin", "src/main.rs", "src/bin", "autobins"), ("example", None, "examples", "autoexamples"),
                ("test", None, "tests", "autotests"), ("bench", None, "benches", "autobenches"))
    for kind, default_main, auto_dir, auto_key in sections:
        declared = data.get(kind) or []
        names = set()
        for entry in declared if isinstance(declared, list) else []:
            name = str(entry.get("name", ""))
            names.add(name)
            found.append(Target(name, [kind], _rel(directory / entry.get("path", f"{auto_dir}/{name}.rs"), root)))
        if pkg.get(auto_key, True) is False:
            continue
        if default_main and (directory / default_main).is_file() and str(pkg["name"]) not in names:
            found.append(Target(str(pkg["name"]), [kind], _rel(directory / default_main, root), declared=False))
        auto = directory / auto_dir
        if auto.is_dir():
            for entry in sorted(auto.iterdir()):
                name = entry.stem if entry.suffix == ".rs" else entry.name
                main = entry if entry.suffix == ".rs" else entry / "main.rs"
                if main.is_file() and name not in names:
                    found.append(Target(name, [kind], _rel(main, root), declared=False))
    build = pkg.get("build", None)
    if build is not False and (isinstance(build, str) or (directory / "build.rs").is_file()):
        script = build if isinstance(build, str) else "build.rs"
        found.append(Target("build-script-build", ["custom-build"], _rel(directory / script, root),
                            declared=isinstance(build, str)))
    return found


def _spec(alias: str, spec: Any) -> dict:
    """A dependency as cargo writes it -- a version string or a table."""
    if isinstance(spec, str):
        return {"version": spec}
    if isinstance(spec, dict):
        return dict(spec)
    raise ValueError(f"dependency `{alias}` is {spec!r}, neither a version nor a table")


def _dependency_tables(data: dict) -> list[tuple[str, str, dict]]:
    """Each dependency table a manifest holds, with its kind and platform."""
    tables: list[tuple[str, str, dict]] = []
    for kind, keys in (("normal", ("dependencies",)), ("dev", ("dev-dependencies", "dev_dependencies")),
                       ("build", ("build-dependencies", "build_dependencies"))):
        for key in keys:
            if isinstance(data.get(key), dict):
                tables.append((kind, "", data[key]))
        for platform, table in (data.get("target") or {}).items():
            for key in keys:
                if isinstance(table, dict) and isinstance(table.get(key), dict):
                    tables.append((kind, str(platform), table[key]))
    return tables


def _dependencies(data: dict, directory: Path, ws: dict | None, by_dir: dict[Path, str],
                  root: Path) -> list[Dependency]:
    found = []
    for kind, platform, table in _dependency_tables(data):
        for alias, spec in table.items():
            spec = _spec(alias, spec)
            base = directory
            if spec.get("workspace") and ws is not None:
                inherited = _spec(alias, ws["dependencies"].get(alias, {}))
                base = root / Path(ws["manifest"]).parent
                spec = {**inherited, **{k: v for k, v in spec.items() if k != "workspace"}}
            name = str(spec.get("package", alias))
            dep = Dependency(name=name, kind=kind, req=str(spec.get("version", "")),
                             alias=alias if alias != name else "", optional=bool(spec.get("optional")),
                             platform=platform)
            if spec.get("path"):
                target_dir = (base / str(spec["path"])).resolve()
                dep.source, dep.path = "path", _rel(target_dir, root)
                dep.name = by_dir.get(target_dir, name)
            elif spec.get("git"):
                dep.source = "git"
            found.append(dep)
    return found


def _apply_lock(reading: Reading, root: Path) -> None:
    """Locked versions from every Cargo.lock beside a workspace or package."""
    toml = _toml()
    seen: set[Path] = set()
    for package in reading.packages:
        lock = None
        # The nearest Cargo.lock at or above the manifest, never above *root*.
        for parent in (root / package.manifest).parents:
            candidate = parent / "Cargo.lock"
            if candidate.is_file():
                lock = candidate
                break
            if parent.resolve() == root.resolve():
                break
        if lock is None or lock in seen:
            continue
        seen.add(lock)
        try:
            data = toml.loads(lock.read_text(encoding="utf-8"))
        except Exception as error:
            reading.notes.append(f"{_rel(lock, root)} did not parse: {error}")
            continue
        for entry in data.get("package", []) or []:
            reading.lock.setdefault(str(entry.get("name")), []).append({
                "version": str(entry.get("version", "")),
                "source": str(entry.get("source", "")),
                "dependencies": [str(d).split(" ")[0] for d in entry.get("dependencies", []) or []],
            })
    for package in reading.packages:
        for dep in package.dependencies:
            versions = reading.lock.get(dep.name, [])
            if len(versions) == 1:
                dep.version = versions[0]["version"]


# ── From cargo's own documents ────────────────────────────────────────────────


def _document(docs_dir: Path, name: str, newest: float, root: Path) -> Document:
    path = docs_dir / name
    doc = Document(name=name, path=_rel(path, root), present=path.is_file())
    if doc.present:
        mtime = path.stat().st_mtime
        doc.generated_at = _iso(mtime)
        doc.age_seconds = round(time.time() - mtime, 1)
        doc.stale = newest > mtime
    else:
        doc.problem = (f"no {name} in {_rel(docs_dir, root)}; `{RECORD_COMMAND} "
                       f"<path>` writes it, and running nothing is all this window does")
    return doc


def _read_metadata(docs_dir: Path, newest_manifest: float, root: Path) -> tuple[Document, dict | None]:
    doc = _document(docs_dir, METADATA_DOCUMENT, newest_manifest, root)
    if not doc.present:
        return doc, None
    try:
        data = json.loads((docs_dir / METADATA_DOCUMENT).read_text(encoding="utf-8"))
    except Exception as error:
        doc.problem = f"{METADATA_DOCUMENT} is not JSON: {error}"
        return doc, None
    # Identity, not presence: a file at that path is cargo's answer only if it
    # has cargo's shape.
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("packages"), list):
        doc.problem = (f"{METADATA_DOCUMENT} is not a `cargo metadata --format-version 1` "
                       f"document (no `version: 1` and `packages` list)")
        return doc, None
    if doc.stale:
        doc.problem = ("written before a manifest last changed, so the manifests were "
                       "read instead; record again to use cargo's resolution")
        return doc, None
    doc.used = True
    return doc, data


def package_name(package_id: str, names: dict[str, str] | None = None) -> str:
    """A package id, in either of cargo's two spellings, to its name.

    `hal 0.1.0 (path+file:///ws/crates/hal)` (before Rust 1.77);
    `path+file:///ws/crates/hal#0.1.0` and
    `registry+https://github.com/rust-lang/crates.io-index#heapless@0.8.0` (after)."""
    if names and package_id in names:
        return names[package_id]
    if " " in package_id:
        return package_id.split(" ", 1)[0]
    url, _, fragment = package_id.partition("#")
    if "@" in fragment:
        return fragment.split("@", 1)[0]
    return url.rstrip("/").rsplit("/", 1)[-1]


def _from_metadata(reading: Reading, data: dict, root: Path) -> None:
    members = set(data.get("workspace_members") or [])
    names = {p["id"]: p["name"] for p in data["packages"] if "id" in p and "name" in p}
    by_id = {p["id"]: p for p in data["packages"] if "id" in p}
    ws_root = Path(data.get("workspace_root") or root)
    reading.workspaces.append({"manifest": "Cargo.toml",
                               "members": sorted(names.get(m, m) for m in members)})
    resolve = {n["id"]: n for n in ((data.get("resolve") or {}).get("nodes") or [])}

    def local(path: str) -> str:
        try:
            return Path(path).relative_to(ws_root).as_posix()
        except ValueError:
            return Path(path).as_posix()

    keep = set(members)
    for member in members:
        for dep in (resolve.get(member) or {}).get("deps", []):
            keep.add(dep.get("pkg", ""))
    for pid in sorted(keep, key=lambda i: names.get(i, i)):
        raw = by_id.get(pid)
        if raw is None:
            continue
        source = str(raw.get("source") or "")
        package = Package(
            name=raw["name"], version=str(raw.get("version", "")),
            manifest=local(raw.get("manifest_path", "")) if pid in members else "",
            edition=str(raw.get("edition", "")), member=pid in members,
            source="local" if not source else ("git" if source.startswith("git+") else "registry"),
            links=str(raw.get("links") or ""),
            features={k: list(v) for k, v in (raw.get("features") or {}).items()},
            resolved_features=list((resolve.get(pid) or {}).get("features", [])),
            workspace="Cargo.toml" if pid in members else "",
        )
        if pid in members:
            package.targets = [Target(t["name"], list(t.get("kind", [])), local(t.get("src_path", "")))
                               for t in raw.get("targets", [])]
            # One package may be declared several times -- `[dependencies]`
            # and `[dev-dependencies]`, or per platform -- each with its own
            # settings, so a declaration is found by kind and platform too.
            declared: dict[tuple[str, str, str], dict] = {}
            for d in raw.get("dependencies", []):
                declared.setdefault((d["name"], d.get("kind") or "normal", d.get("target") or ""), d)

            def declaration(name: str, kind: str, platform: str) -> dict:
                return (declared.get((name, kind, platform))
                        or next((d for (n, k, _), d in declared.items() if (n, k) == (name, kind)), None)
                        or next((d for (n, _, _), d in declared.items() if n == name), {}))

            node = resolve.get(pid)
            if node is not None:
                for dep in node.get("deps", []):
                    target_pkg = by_id.get(dep.get("pkg", ""), {})
                    name = target_pkg.get("name", dep.get("name", ""))
                    for dk in dep.get("dep_kinds") or [{"kind": None, "target": None}]:
                        spec = declaration(name, dk.get("kind") or "normal", dk.get("target") or "")
                        package.dependencies.append(Dependency(
                            name=name, kind=dk.get("kind") or "normal", req=str(spec.get("req", "")),
                            alias=spec.get("rename") or "", optional=bool(spec.get("optional")),
                            platform=dk.get("target") or "",
                            source="path" if spec.get("path") else ("git" if str(spec.get("source") or "").startswith("git+") else "registry"),
                            version=str(target_pkg.get("version", ""))))
            else:
                for spec in raw.get("dependencies", []):
                    package.dependencies.append(Dependency(
                        name=spec["name"], kind=spec.get("kind") or "normal", req=str(spec.get("req", "")),
                        optional=bool(spec.get("optional")), platform=spec.get("target") or ""))
        reading.packages.append(package)

    # Dependencies of dependencies, as cargo resolved them: what `transitive`
    # draws -- the lockfile is read only when the manifests answer.
    for pid, node in resolve.items():
        raw = by_id.get(pid, {})
        reading.lock.setdefault(package_name(pid, names), []).append({
            "version": str(raw.get("version", "")),
            "source": str(raw.get("source") or ""),
            "dependencies": [package_name(str(d.get("pkg", "")), names) for d in node.get("deps", [])],
        })


def _read_check(reading: Reading, docs_dir: Path, root: Path) -> Document:
    """Diagnostics, artifacts and build-script facts from check.jsonl -- only
    while it is current. A check recorded before a source or manifest last
    changed is not used, as a stale metadata.json is not: what rustc said
    then, drawn now, is a stale answer delivered as current."""
    doc = _document(docs_dir, CHECK_DOCUMENT, reading.newest_source, root)
    if not doc.present:
        return doc
    if doc.stale:
        doc.problem = ("a source or manifest changed after this check was recorded, so nothing "
                       f"in it is drawn; `{RECORD_COMMAND} <path>` records it again")
        return doc
    names: dict[str, str] = {}
    try:
        lines = (docs_dir / CHECK_DOCUMENT).read_text(encoding="utf-8").splitlines()
    except Exception as error:
        doc.problem = f"{CHECK_DOCUMENT} could not be read: {error}"
        return doc
    unreadable = 0
    for line in lines:
        if not line.strip().startswith("{"):
            continue  # cargo interleaves plain text when asked to
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            unreadable += 1
            continue
        reason = message.get("reason")
        package = package_name(str(message.get("package_id", "")), names)
        target = (message.get("target") or {}).get("name", "")
        if reason == "compiler-message":
            if len(reading.diagnostics) >= MAX_DIAGNOSTICS:
                continue
            body = message.get("message") or {}
            spans = body.get("spans") or []
            if not spans and (body.get("level") == "failure-note"
                              or RUN_SUMMARY.match(str(body.get("message", "")))):
                continue
            primary = next((s for s in spans if s.get("is_primary")), spans[0] if spans else {})
            reading.diagnostics.append(Diagnostic(
                level=str(body.get("level", "")), message=str(body.get("message", "")),
                package=package, target=target,
                code=str((body.get("code") or {}).get("code", "") or ""),
                file=str(primary.get("file_name", "")).replace("\\", "/"),
                line=int(primary.get("line_start", 0) or 0),
                kinds=list((message.get("target") or {}).get("kind", []))))
        elif reason == "compiler-artifact":
            reading.artifacts.append({
                "package": package, "target": target,
                "kinds": list((message.get("target") or {}).get("kind", [])),
                "features": list(message.get("features") or []),
                "fresh": bool(message.get("fresh")),
                "profile": (message.get("profile") or {}).get("opt_level", ""),
            })
        elif reason == "build-script-executed":
            reading.scripts.append({
                "package": package,
                "linked_libs": list(message.get("linked_libs") or []),
                "linked_paths": list(message.get("linked_paths") or []),
                "cfgs": list(message.get("cfgs") or []),
            })
        elif reason == "build-finished":
            reading.build_success = bool(message.get("success"))
    doc.used = True
    if len(reading.diagnostics) >= MAX_DIAGNOSTICS:
        reading.notes.append(f"stopped at the diagnostic bound ({MAX_DIAGNOSTICS}); later ones are not drawn")
    if unreadable:
        reading.notes.append(f"{unreadable} line(s) of {CHECK_DOCUMENT} were not JSON and were skipped")
    if reading.build_success is None:
        # cargo writes `build-finished` last; without it the check stopped
        # first -- before compiling, or at a timeout.
        doc.problem = "it holds no build-finished message, so cargo stopped before the check finished"
    return doc


# ── Firmware facts ────────────────────────────────────────────────────────────


def _no_std(root: Path, package: Package) -> str:
    """`yes`, `conditional` (`cfg_attr(.., no_std)`), or empty.

    A manifest may name any path as a target's source -- `/dev/zero`, a FIFO,
    another checkout's file -- and this runs in a route, so only a regular
    file inside the package's directory is read, and only its head."""
    directory = (root / package.manifest).parent.resolve()
    for target in package.targets:
        if not set(target.kinds) & {"lib", "bin", "rlib", "staticlib", "cdylib"}:
            continue
        path = (root / target.src).resolve()
        if not _under(path, directory) or not path.is_file():
            continue
        try:
            with path.open("rb") as handle:
                head = handle.read(65536).decode("utf-8", "replace")
        except OSError:
            continue
        if re.search(r"#!\[\s*no_std\s*\]", head):
            return "yes"
        if re.search(r"#!\[\s*cfg_attr\([^\]]*\bno_std\b", head):
            return "conditional"
    return ""


def _firmware(root: Path, reading: Reading, memory_maps: list[Path], toml) -> dict[str, Any]:
    """What `.cargo/config.toml` says the build is for. Read, never run: a
    `runner` is shown as the text it is."""
    facts: dict[str, Any] = {"build_targets": [], "runners": {}, "linker_scripts": [],
                             "memory_maps": sorted(_rel(m, root) for m in memory_maps),
                             "config": ""}
    for name in ("config.toml", "config"):
        path = root / ".cargo" / name
        if not path.is_file():
            continue
        try:
            data = toml.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            reading.notes.append(f"{_rel(path, root)} did not parse: {error}")
            break
        try:
            return {**facts, **_config_facts(data), "config": _rel(path, root)}
        except Exception as error:
            reading.notes.append(f"{_rel(path, root)} has a shape this reader does not take "
                                 f"({error}), so no device target is drawn from it")
            break
    return facts


def _flags(value: Any) -> list[str]:
    """`rustflags` as cargo takes it: a list, or one space-separated string."""
    if isinstance(value, str):
        return value.split()
    return [str(flag) for flag in value or []]


def _config_facts(data: dict) -> dict[str, Any]:
    facts: dict[str, Any] = {"runners": {}}
    build = data.get("build") or {}
    targets = build.get("target") or []
    facts["build_targets"] = [targets] if isinstance(targets, str) else list(targets)
    flags = _flags(build.get("rustflags"))
    for triple, table in (data.get("target") or {}).items():
        if isinstance(table, dict):
            if table.get("runner"):
                runner = table["runner"]
                facts["runners"][triple] = runner if isinstance(runner, str) else " ".join(runner)
            flags += _flags(table.get("rustflags"))
    scripts = []
    for i, flag in enumerate(flags):
        flag = str(flag)
        for prefix in ("link-arg=-T", "-Clink-arg=-T"):
            if prefix in flag:
                scripts.append(flag.split(prefix, 1)[1])
        if flag == "-T" and i + 1 < len(flags):
            scripts.append(str(flags[i + 1]))
    facts["linker_scripts"] = sorted(set(scripts))
    return facts


# ── The graph ─────────────────────────────────────────────────────────────────


def _look(kind: str) -> dict[str, Any]:
    shape, color = LOOKS[kind]
    return {"shape": shape, "color": color}


def _diagnostic_counts(diagnostics: list[Diagnostic]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in diagnostics:
        counts[d.level] = counts.get(d.level, 0) + 1
    return counts


def _count_label(counts: dict[str, int]) -> str:
    parts = [f"{counts[level]} {level}{'s' if counts[level] != 1 else ''}"
             for level in ("error", "warning") if counts.get(level)]
    return " · " + ", ".join(parts) if parts else ""


def as_graph(reading: Reading, features: bool = False, transitive: bool = False):
    """The workspace as a `networkx` graph the serializer accepts.

    **EVERY EDGE IS ONE A MANIFEST, THE LOCKFILE OR CARGO DECLARED.** Nothing is
    added to make the picture connected. A dependency's kind is its colour *and*
    its label, so no fact rides on colour alone; a dev-dependency is dashed
    because it never reaches the built artifact, and an optional or
    platform-specific one says its condition on the edge.
    """
    import networkx as nx

    graph = nx.MultiDiGraph(kind="cargo", source=reading.root, engine=reading.engine)

    for ws in reading.workspaces:
        ws_id = f"workspace::{ws['manifest']}"
        label = Path(ws["manifest"]).parent.name or Path(reading.root).name
        graph.add_node(ws_id, label=label, kind="workspace", depth=0, **_look("workspace"),
                       hover=f"workspace {ws['manifest']}",
                       click=f"<p>Workspace <code>{ws['manifest']}</code></p>")

    member_ids: dict[str, str] = {}
    for package in reading.packages:
        node_id = f"crate::{package.name}"
        kind = "crate" if package.member else "external_crate"
        member_ids[package.name] = node_id
        counts = _diagnostic_counts([d for d in reading.diagnostics if d.package == package.name])
        no_std = {"yes": "no_std", "conditional": "no_std (conditional)"}.get(package.no_std, "")
        facts = [f for f in (package.edition and f"edition {package.edition}", no_std,
                             package.links and f"links {package.links}") if f]
        graph.add_node(
            node_id, label=f"{package.name} {package.version}".strip() + _count_label(counts),
            kind=kind, depth=1 if package.member else 2, **_look(kind),
            meta={"version": package.version, "edition": package.edition,
                  "source": package.source, "no_std": package.no_std, "links": package.links,
                  "manifest": package.manifest, "diagnostics": counts,
                  "features": sorted(package.features),
                  "resolved_features": package.resolved_features,
                  "memory_maps": package.memory_maps},
            hover=f"{package.name} {package.version} — " + (", ".join(facts) or package.source),
            click=_click_for_package(package, counts))
        if package.workspace:
            graph.add_edge(f"workspace::{package.workspace}", node_id, kind="contains", label="member")

    # Externals a manifest names but the reading has no package for.
    for package in [p for p in reading.packages if p.member]:
        for dep in package.dependencies:
            if dep.name not in member_ids:
                ext_id = f"crate::{dep.name}"
                member_ids[dep.name] = ext_id
                graph.add_node(ext_id, label=f"{dep.name} {dep.version or dep.req}".strip(),
                               kind="external_crate", depth=2, **_look("external_crate"),
                               meta={"version": dep.version, "req": dep.req, "source": dep.source},
                               hover=f"{dep.name} {dep.version or dep.req} ({dep.source})")

    for package in [p for p in reading.packages if p.member]:
        crate_id = member_ids[package.name]
        script_id = ""
        for target in package.targets:
            target_id = f"target::{package.name}::{'/'.join(target.kinds)}::{target.name}"
            kind0 = target.kinds[0] if target.kinds else "lib"
            shape, color = TARGET_LOOKS.get(kind0, ("square", "#4a9eff"))
            mine = [d for d in reading.diagnostics if d.package == package.name and
                    ((d.target == target.name and (not d.kinds or set(d.kinds) & set(target.kinds)))
                     or (not d.target and kind0 == "lib"))]
            counts = _diagnostic_counts(mine)
            label = "build.rs" if kind0 == "custom-build" else f"{kind0} {target.name}"
            graph.add_node(target_id, label=label + _count_label(counts), kind="target", depth=2,
                           shape=shape, color=color,
                           meta={"kinds": target.kinds, "src": target.src, "declared": target.declared,
                                 "diagnostics": counts,
                                 "messages": [f"{d.level}: {d.message} ({d.file}:{d.line})" for d in mine[:20]]},
                           file=target.src,
                           hover=f"{label} — {target.src}" + (f" — {mine[0].level}: {mine[0].message}" if mine else ""))
            graph.add_edge(crate_id, target_id, kind="contains", label="target")
            if kind0 == "custom-build":
                script_id = target_id
        for dep in package.dependencies:
            source_id = script_id if (dep.kind == "build" and script_id) else crate_id
            label = dep.kind if dep.kind != "normal" else "depends"
            conditions = [c for c in (dep.optional and "optional", dep.platform) if c]
            if conditions:
                label += f" ({', '.join(conditions)})"
            graph.add_edge(source_id, member_ids[dep.name], kind="depends_on", label=label,
                           dep_kind=dep.kind, optional=dep.optional, platform=dep.platform,
                           req=dep.req, **EDGE_LOOKS.get(dep.kind, EDGE_LOOKS["normal"]),
                           **({"style": "dashed"} if dep.optional or dep.platform else {}))
        if package.links:
            native_id = f"native::{package.links}"
            graph.add_node(native_id, label=f"native {package.links}", kind="native_lib", depth=2,
                           **_look("native_lib"), hover=f"`links = \"{package.links}\"` in {package.manifest}")
            graph.add_edge(script_id or crate_id, native_id, kind="links", label="links (declared)")
        for memory in package.memory_maps:
            mem_id = f"memory::{memory}"
            graph.add_node(mem_id, label=Path(memory).name, kind="memory_map", depth=2,
                           **_look("memory_map"), file=memory,
                           hover=f"{memory} — the device's memory, read by the linker")
            graph.add_edge(crate_id, mem_id, kind="links", label="memory map")

    for script in reading.scripts:
        owner = next((p for p in reading.packages if p.name == script["package"] and p.member), None)
        if owner is None:
            continue
        source_id = next((n for n in graph.successors(member_ids[owner.name])
                          if graph.nodes[n].get("meta", {}).get("kinds") == ["custom-build"]),
                         member_ids[owner.name])
        for lib in script["linked_libs"]:
            kind_name, _, name = lib.rpartition("=")
            native_id = f"native::{name}"
            graph.add_node(native_id, label=f"native {name}", kind="native_lib", depth=2,
                           **_look("native_lib"), meta={"link_kind": kind_name or "default"},
                           hover=f"cargo:rustc-link-lib={lib}, from {owner.name}'s build script")
            graph.add_edge(source_id, native_id, kind="links", label=f"links {kind_name or ''}".strip(),
                           measured=True)

    for triple in reading.firmware.get("build_targets", []):
        triple_id = f"device::{triple}"
        runner = reading.firmware.get("runners", {}).get(triple, "")
        graph.add_node(triple_id, label=triple, kind="device_target", depth=1, **_look("device_target"),
                       meta={"runner": runner},
                       hover=f"builds for {triple}" + (f"; runner `{runner}` (shown, never run)" if runner else ""))
        # A device target is the workspace's, or each crate's when there is none.
        owners = [f"workspace::{ws['manifest']}" for ws in reading.workspaces] or [
            member_ids[p.name] for p in reading.packages if p.member]
        for owner in owners:
            graph.add_edge(owner, triple_id, kind="builds_for", label="builds for")

    if features:
        for package in [p for p in reading.packages if p.member]:
            for feature, enables in package.features.items():
                feature_id = f"feature::{package.name}::{feature}"
                on = feature in package.resolved_features
                graph.add_node(feature_id, label=f"{feature}{' ✓' if on else ''}", kind="feature", depth=3,
                               **_look("feature"), meta={"enabled": on},
                               hover=f"feature {feature} of {package.name}" + (" — enabled in the resolution" if on else ""))
                graph.add_edge(member_ids[package.name], feature_id, kind="declares", label="feature")
            for feature, enables in package.features.items():
                for item in enables:
                    item = str(item)
                    if item.startswith("dep:"):
                        target = member_ids.get(item[4:])
                    elif "/" in item:
                        target = member_ids.get(item.split("/", 1)[0].rstrip("?"))
                    else:
                        target = f"feature::{package.name}::{item}"
                    if target and target in graph:
                        graph.add_edge(f"feature::{package.name}::{feature}", target, kind="enables",
                                       label="enables")

    if transitive:
        # Whose answer an edge is: cargo's resolution, or the lockfile's.
        how = "resolved" if reading.engine == "cargo metadata" else "locked"
        for name, entries in reading.lock.items():
            source = member_ids.get(name)
            if source is None or len(entries) != 1:
                continue
            for dep in entries[0]["dependencies"]:
                target = member_ids.get(dep)
                if target is None:
                    versions = reading.lock.get(dep, [])
                    target = f"crate::{dep}"
                    member_ids[dep] = target
                    graph.add_node(target, label=f"{dep} {versions[0]['version'] if len(versions) == 1 else ''}".strip(),
                                   kind="external_crate", depth=3, **_look("external_crate"),
                                   hover=f"{dep}, {how}")
                if not graph.has_edge(source, target):
                    graph.add_edge(source, target, kind="depends_on", label=how,
                                   color=EDGE_LOOKS["normal"]["color"], size=1)
    return graph


def _click_for_package(package: Package, counts: dict[str, int]) -> str:
    deps = "".join(f"<li>{d.name} <i>{d.kind}</i> {d.version or d.req}</li>" for d in package.dependencies[:30])
    return (f"<p><b>{package.name}</b> {package.version}</p>"
            f"<p>{package.manifest or package.source}</p>"
            + (f"<p>no_std: {package.no_std}</p>" if package.no_std else "")
            + (f"<p>Diagnostics: {counts}</p>" if counts else "")
            + (f"<ul>{deps}</ul>" if deps else ""))


def caveat(reading: Reading) -> str:
    """The sentences a reader needs before believing the picture."""
    parts = []
    if reading.engine == "cargo metadata":
        parts.append("Dependencies, versions and features are cargo's own resolution, "
                     "from metadata.json.")
    else:
        parts.append("Read from the manifests without running cargo: features are as "
                     "declared rather than resolved, every platform's dependencies are "
                     "drawn at once with their cfg on the edge, and a version is the "
                     "lockfile's when it has exactly one.")
    check = next((d for d in reading.documents if d.name == CHECK_DOCUMENT), None)
    if check is None or not check.present:
        parts.append("No check.jsonl was recorded, so no diagnostics are drawn -- which "
                     "is not the same as a clean build.")
    elif not check.used:
        parts.append(f"check.jsonl was not used ({check.problem}), so no diagnostics are drawn "
                     f"from it -- which is not the same as a clean build.")
    else:
        parts.append(f"Diagnostics are what rustc said at {check.generated_at}.")
        if reading.build_success is None:
            parts.append("That check never finished -- check.jsonl holds no build-finished "
                         "message -- so a crate with no diagnostic in it is not a clean one.")
    if reading.notes:
        parts.append(" ".join(reading.notes))
    return " ".join(parts)


def metadata(reading: Reading, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas, the provenance strip and any client read."""
    used = [d for d in reading.documents if d.used]
    return {
        "kind": "cargo",
        "source": reading.root,
        "engine": reading.engine,
        "generated_at": max((d.generated_at for d in used), default="") or _iso(time.time()),
        "layout": getattr(options, "layout", "Kamada Kawai"),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        "packages": sum(1 for p in reading.packages if p.member),
        "external": sum(1 for p in reading.packages if not p.member),
        "diagnostics": _diagnostic_counts(reading.diagnostics),
        "build_success": reading.build_success,
        "documents": [asdict(d) for d in reading.documents],
        "firmware": reading.firmware,
        "caveat": caveat(reading),
    }


def as_gjgf(reading: Reading, options: Any = None, features: bool = False,
            transitive: bool = False) -> dict[str, Any]:
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout="Kamada Kawai")
    return GraphSerializer.serialize_to_gjgf(as_graph(reading, features, transitive), chosen)


def as_data(reading: Reading) -> dict[str, Any]:
    """The reading itself, without a layout -- comparable with what cargo says."""
    return {
        "root": reading.root,
        "engine": reading.engine,
        "workspaces": reading.workspaces,
        "packages": [asdict(p) for p in reading.packages],
        "documents": [asdict(d) for d in reading.documents],
        "diagnostics": [asdict(d) for d in reading.diagnostics],
        "artifacts": reading.artifacts,
        "scripts": reading.scripts,
        "build_success": reading.build_success,
        "firmware": reading.firmware,
        "notes": reading.notes,
        "caveat": caveat(reading),
    }


def recorded_diagnostics(root: Path | str) -> Reading | None:
    """Only what `check.jsonl` under *root* recorded, and whether a source has
    changed since: what the parse pipeline needs to put diagnostics on the
    code map. None when there is no such document.

    Staleness is the full read's -- the same walk, without parsing a manifest
    -- so the code map and `/cargo` never disagree about it, and a stale check
    is not used here either: its lines would name whatever item sits there
    now, and its complaints are rustc's then."""
    root = Path(root)
    docs_dir = root / DOCUMENTS
    if not (docs_dir / CHECK_DOCUMENT).is_file():
        return None
    reading = Reading(root=str(root))
    reading.newest_source, _ = _walk(root, reading, [], [])
    reading.documents.append(_read_check(reading, docs_dir, root))
    return reading


def annotate_diagnostics(graph, reading: Reading) -> int:
    """Stamp `meta.diagnostics` on the Rust items of a parsed code graph whose
    lines contain a recorded diagnostic. Returns how many items it touched.

    Joined by path suffix and line range: a diagnostic at `crates/hal/src/uart.rs:12`
    lands on the item in that file whose `line`..`line_end` holds line 12, the
    innermost when several do. A diagnostic no item holds is left unjoined --
    `/cargo/data` still lists it.

    The check document's row -- present, used, stale, and why not -- is
    `graph.graph["recorded_check"]`, so a code map with nothing on it says
    whether that is a clean check or one that was not used."""
    check = next((doc for doc in reading.documents if doc.name == CHECK_DOCUMENT), None)
    if check is not None:
        graph.graph["recorded_check"] = asdict(check)
    by_file: dict[str, list[Diagnostic]] = {}
    for d in reading.diagnostics:
        if d.file:
            by_file.setdefault(d.file, []).append(d)
    if not by_file:
        return 0
    touched = 0
    candidates: dict[str, list[tuple[str, dict]]] = {}
    for node_id, data in graph.nodes(data=True):
        if data.get("language") != "rust" or not data.get("line"):
            continue
        path = str(data.get("file", "")).replace("\\", "/")
        for diag_file in by_file:
            if path.endswith(diag_file) or path.endswith("/" + diag_file):
                candidates.setdefault(diag_file, []).append((node_id, data))
    for diag_file, nodes in candidates.items():
        for d in by_file[diag_file]:
            holding = [(n, data) for n, data in nodes
                       if data["line"] <= d.line <= (data.get("meta") or {}).get("line_end", data["line"])]
            if not holding:
                continue
            node_id, data = max(holding, key=lambda nd: (nd[1].get("depth", 0), nd[1]["line"]))
            meta = data.setdefault("meta", {})
            diags = meta.setdefault("diagnostics", {})
            diags[d.level] = diags.get(d.level, 0) + 1
            meta.setdefault("messages", []).append(f"{d.level}: {d.message} (line {d.line})")
            # Provenance travels with the figure: when rustc said it.
            meta["diagnostics_recorded_at"] = check.generated_at if check else ""
            if d.level == "error":
                data["has_parse_warning"] = True
            touched += 1
    return touched
