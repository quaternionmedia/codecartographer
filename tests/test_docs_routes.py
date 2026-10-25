"""The documents say what the application says.

Every tracked Markdown file outside the two submodules is read against the tree
it describes, and each check here fails on a document that disagrees with it:

- every prefix `codecarto.main.app` mounts appears in `docs/api.md`'s overview
  table and under one of its headings, and in `web/vite.config.js`'s
  `API_PATHS`;
- every route a document names is mounted, unless `UNSERVED_ROUTES` names it
  as planned, and every route the OpenAPI schema (`/docs`) leaves out is named
  in `docs/api.md`;
- the README is an onramp: at most `README_LINES` lines;
- no document names the port this project no longer binds, or a test count;
- every relative link resolves, and so does every repository path written in
  backticks in prose, unless `EXAMPLE_PATHS` names it;
- every `codecarto ...` command a document writes exists in the click tree,
  with its options, and a value from a fixed choice is one of the choices;
- every JSON envelope in `docs/api.md` has `status`, `message` and `results`;
- every environment variable the code reads is in `docs/cli.md`'s table, and
  every one a document names is read by the code;
- every sync a document or the code tells a reader to run is `ONE_SYNC`;
- `docs/index.md` links every page under `docs/`;
- the UI reference names every registered panel, and the default layout and
  the source tree agree with the registry and the dev proxy;
- every statement of the graph cache key names the schema version
  `cache_service._make_key` hashes with the url, mode, layout and extensions;
- the caches section says what evicting a GitHub repository from either cache
  removes, as the two evictions do;
- a C edge kind is named in upper case only about `/c-parser/*`, and in lower
  case only as `c_language_parser._EDGE_KIND_MAP` gives it;
- every depth table's row 3 names what the C adapter puts at depth 3.

The application, the click tree and the code are the sources; nothing here
keeps a list of routes, commands or variables of its own.

WHAT THIS CANNOT SEE. Whether a description is right: it checks that what a
document names exists, not that the sentence about it is true. A route is read
only where it is written after its method or `$API`, or in backticks under a
prefix the application mounts, so a bare `/name` elsewhere is not a claim it
checks. Paths into a submodule, and graphbase's `/db` routes, are checked only
where the submodule is checked out, which CI does not do.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import click
import pytest

ROOT = Path(__file__).resolve().parents[1]

# Served by the application and not documented as API: FastAPI's own pages,
# the built web application and its assets, and the root redirect.
NOT_API = {"", "app", "assets", "docs", "redoc", "openapi.json"}

SUBMODULES = ("governance", "graphbase")


def _tracked_documents() -> list[Path]:
    """Every tracked `*.md` outside the submodules, each file once.

    A symlink (`CLAUDE.md`, `.github/copilot-instructions.md`) is read under
    its target's name. Outside a git checkout, every `*.md` under the root
    that is not in a submodule, a dependency or a build directory.
    """
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-s", "--", "*.md"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", "node_modules", ".venv", "dist", *SUBMODULES}
        return sorted(p for p in ROOT.rglob("*.md")
                      if not p.is_symlink()
                      and not skip & set(p.relative_to(ROOT).parts))
    found = []
    for line in listing.splitlines():
        meta, _, name = line.partition("\t")
        if meta.split()[0] == "120000" or name.split("/")[0] in SUBMODULES:
            continue
        found.append(ROOT / name)
    return sorted(found)


DOCUMENTS = _tracked_documents()


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _prose_lines(path: Path):
    """(line number, line, inside a fenced code block) for each line."""
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        yield number, line, fenced


def test_the_document_set_is_every_tracked_markdown_file():
    names = {_rel(p) for p in DOCUMENTS}
    assert {"README.md", "AGENTS.md", ".github/CONTRIBUTING.md",
            "docs/index.md"} <= names, names
    assert not any(n.split("/")[0] in SUBMODULES for n in names)


# ── Routes ───────────────────────────────────────────────────────────────────


def _prefixes() -> set[str]:
    """Every first path segment the application mounts, as `/name`."""
    from codecarto.main import app

    found = set()
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        segment = path.strip("/").split("/")[0]
        if segment in NOT_API:
            continue
        found.add(f"/{segment}")
    return found


@pytest.fixture(scope="module")
def prefixes() -> set[str]:
    found = _prefixes()
    # `/db` mounts only under MONGODB_URI; it is documented either way, so it is
    # asserted either way rather than depending on the shell this runs in.
    found.add("/db")
    assert found, "the application mounts no routes, which is not a documented API"
    return found


def test_api_overview_table_names_every_mounted_prefix(prefixes):
    api = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    overview = re.search(r"^## Overview\n(.*?)(?=^## )", api, re.M | re.S)
    assert overview, "docs/api.md has no '## Overview' section"
    missing = sorted(p for p in prefixes if f"| `{p}` |" not in overview.group(1))
    assert not missing, f"docs/api.md's overview table lacks a row for: {missing}"


README_LINES = 60


def test_the_readme_is_an_onramp():
    """What the README would add past this belongs on a page under `docs/`."""
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= README_LINES, (
        f"README.md is {len(lines)} lines; move the depth to docs/ and link it")


def test_api_reference_has_a_heading_for_every_mounted_prefix(prefixes):
    api = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    headings = [line for line in api.splitlines() if line.startswith("#")]
    missing = sorted(p for p in prefixes
                     if not any(p in h for h in headings))
    assert not missing, f"docs/api.md has no heading naming: {missing}"


# FastAPI's own pages, the root redirect and the build's static files: served,
# and not routes a reader calls.
FRAMEWORK = {"", "docs", "redoc", "openapi.json", "assets"}


def test_api_reference_names_every_route_the_schema_leaves_out():
    """`/docs` lists the OpenAPI schema, which has no WebSockets and none of
    the routes kept out of it; `serve --help` sends a reader to `docs/api.md`
    for those."""
    from codecarto.main import app

    schema = set(app.openapi()["paths"])
    left_out = sorted({path.rstrip("/") for route in app.routes
                       if (path := getattr(route, "path", "")) not in schema
                       and path.strip("/").split("/")[0] not in FRAMEWORK})
    assert left_out, "the schema has every route; serve --help's sentence is stale"
    api = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    named = {p.rstrip("/") for p in re.findall(r"`(?:[A-Z]+ )?(/[^`\s?]*)", api)}
    missing = [p for p in left_out if p not in named]
    assert not missing, (
        f"/docs does not list these and docs/api.md does not name them, so a "
        f"reader of either cannot find them: {missing}")


def test_dev_server_proxies_every_mounted_prefix(prefixes):
    """A prefix absent from `API_PATHS` is a request Vite answers itself."""
    config = (ROOT / "web" / "vite.config.js").read_text(encoding="utf-8")
    block = re.search(r"const API_PATHS = \[(.*?)\];", config, re.S)
    assert block, "web/vite.config.js has no API_PATHS list"
    listed = set(re.findall(r"'(/[^']*)'", block.group(1)))
    missing = sorted(p for p in prefixes if p not in listed)
    assert not missing, f"web/vite.config.js API_PATHS lacks: {missing}"


# A document names a route when it writes one after its method or after `$API`,
# fenced or not, or in backticks in prose with a first segment the application
# mounts. `{name}` and `<name>` are a parameter; a trailing `*` or `...` is
# everything under the path before it.
METHOD_ROUTE = re.compile(
    r"\b(?:GET|POST|PUT|PATCH|DELETE|WebSocket)\s+`?(/[A-Za-z][^\s`|)\"',]*)")
API_ROUTE = re.compile(r"\$API(/[A-Za-z][^\s`|)\"',]*)")
SPAN_ROUTE = re.compile(r"`(/[A-Za-z][^`\s]*)`")

# Routes a document names that nothing mounts, each for a stated reason.
UNSERVED_ROUTES = {
    "/parse/repo": "planned in docs/roadmap/large-repos.md, A whole repository in one request",
    "/parse/job": "planned in docs/roadmap/large-repos.md, Parse jobs",
    "/parse/job/{id}/ws": "planned in docs/roadmap/large-repos.md, Parse jobs",
}


def _segments(path: str) -> tuple[str, ...]:
    path = re.split(r"[?#]", path)[0].rstrip(".,:;")
    return tuple(path.strip("/").split("/"))


def _parameter(segment: str) -> bool:
    return segment[:1] in "{<" and segment[-1:] in "}>"


def _mounted_routes() -> tuple[list[tuple[str, ...]], bool]:
    """Every path the application serves, as segments, and whether graphbase's
    are among them. Those mount under `/db` only with `MONGODB_URI`, so they
    are read from graphbase's router, where the submodule is checked out."""
    from codecarto.main import app

    paths = [getattr(route, "path", "") or "" for route in app.routes]
    try:
        from graphbase import graphdb
    except Exception:  # not checked out, as in CI
        graphbase = False
    else:
        paths += [f"/db{route.path}" for route in graphdb.routes]
        graphbase = True
    return [_segments(p) for p in paths if p.strip("/")], graphbase


def _serves(mounted: list[tuple[str, ...]], written: tuple[str, ...]) -> bool:
    """A route is mounted at `written`, or under it."""
    if written[-1] in ("*", "..."):
        written = written[:-1]
    return any(len(route) >= len(written)
               and all(w == r or _parameter(r) for w, r in zip(written, route))
               for route in mounted)


def _route_mentions(first_segments: set[str]):
    """(document, line, the route as written) for every route a document names."""
    for path in DOCUMENTS:
        for number, line, fenced in _prose_lines(path):
            found = METHOD_ROUTE.findall(line) + API_ROUTE.findall(line)
            if not fenced:
                found += [s for s in SPAN_ROUTE.findall(line)
                          if _segments(s)[0] in first_segments]
            for written in dict.fromkeys(found):
                yield path, number, written


def test_every_route_a_document_names_is_mounted():
    mounted, graphbase = _mounted_routes()
    unserved = {_segments(p) for p in UNSERVED_ROUTES}
    wrong = []
    for path, number, written in _route_mentions({r[0] for r in mounted}):
        segments = _segments(written)
        if segments in unserved or (segments[0] == "db" and not graphbase):
            continue
        if not _serves(mounted, segments):
            wrong.append(f"{_rel(path)}:{number}: {written}")
    assert not wrong, (
        "these documents name routes nothing mounts; repair them, or name a "
        f"planned one in UNSERVED_ROUTES with the reason: {wrong}")


def test_the_route_reader_sees_routes():
    """The reader finds routes written each way, so a green result is not an
    empty one."""
    mounted, _ = _mounted_routes()
    seen = {w for _, _, w in _route_mentions({r[0] for r in mounted})}
    assert {"/parse/unified", "/pam/ws/live", "/lexicon/{language}/graph",
            "/c-parser/cache/git-git"} <= seen, sorted(seen)


def test_unserved_routes_are_still_unserved():
    """An allowance for a route that has since been mounted is a stale exemption."""
    mounted, _ = _mounted_routes()
    served = sorted(p for p in UNSERVED_ROUTES if _serves(mounted, _segments(p)))
    assert not served, f"UNSERVED_ROUTES exempts routes that are mounted: {served}"


def test_no_document_names_the_port_this_project_no_longer_binds():
    from codecarto.cli import DEFAULT_PORT

    retired = "8000"
    assert str(DEFAULT_PORT) != retired, (
        "the default port is the retired one again; this check's premise is "
        "gone and it should be rewritten, not deleted")
    stale = []
    for path in DOCUMENTS:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"(localhost|127\.0\.0\.1):{retired}\b", line):
                stale.append(f"{_rel(path)}:{number}")
    assert not stale, (
        f"these lines name :{retired}, which this project stopped binding; "
        f"the constant is codecarto.cli.DEFAULT_PORT and `serve --help` prints "
        f"it: {stale}")


def test_documents_do_not_restate_the_test_count():
    """The command is what a reader needs; the figure is what it prints."""
    offenders = []
    for path in DOCUMENTS:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\b\d{3,}\s+tests\b", line):
                offenders.append(f"{_rel(path)}:{number}: {line.strip()}")
    assert not offenders, f"a test count in durable text: {offenders}"


def test_no_document_runs_node_test_on_a_directory():
    """`node --test tests/rad/` runs the directory on Node 20; Node 22, which the
    web workflow uses, reads it as a module path and fails with `Cannot find
    module`. The suites run through `web/scripts/node-test.mjs`, which names the
    files, so a document or a test's header giving the directory form gives a
    command that fails where CI runs.
    """
    web = ROOT / "web"
    offenders = []
    for path in (*DOCUMENTS, *sorted((web / "tests").rglob("*.mjs"))):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for argument in re.findall(r"node --test\s+([\w./-]+)", line):
                if argument.endswith("/") or (web / argument).is_dir():
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}:{number}: {argument}")
    assert not offenders, (
        f"these run `node --test` on a directory, which fails on Node 22; the "
        f"suites run as `node scripts/node-test.mjs <dir>` from web/: {offenders}")


# ── Links and paths ──────────────────────────────────────────────────────────

LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
# A repository path in backticks starts with one of the tree's top-level
# directories. A bare file name or a path relative to some other base is not
# read as a claim about the tree.
REPO_PATH = re.compile(
    r"^(?:\./)?((?:codecarto|web|tests|docs|examples|governance|graphbase|"
    r"\.github|LICENSES)/[^\s:#]*)")

# Paths a document names that are not in the tree, each for a stated reason.
EXAMPLE_PATHS = {
    "web/dist": "the build's output, written by `npm run build` and not tracked",
    "codecarto/routers/parse_job_router.py": "planned in the large-repository roadmap",
    "codecarto/services/parse_job_service.py": "planned in the large-repository roadmap",
}


def _in_unchecked_submodule(target: Path) -> bool:
    """A path into a submodule that is not checked out cannot be read."""
    try:
        parts = target.resolve().relative_to(ROOT.resolve()).parts
    except ValueError:
        return False
    if not parts or parts[0] not in SUBMODULES:
        return False
    module = ROOT / parts[0] / ("qm" if parts[0] == "governance" else "")
    return not any(module.iterdir()) if module.is_dir() else True


def _references():
    """(document, line, what was written, the path it names) for every
    relative link and every repository path in backticks in prose."""
    for path in DOCUMENTS:
        for number, line, fenced in _prose_lines(path):
            if fenced:
                continue
            for match in LINK.finditer(line):
                target = match.group(1)
                if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#)", target):
                    continue
                target = target.split("#")[0].split("?")[0]
                if target:
                    yield path, number, target, path.parent / target
            for span in CODE_SPAN.findall(line):
                found = REPO_PATH.match(span.strip())
                if not found:
                    continue
                written = found.group(1).split("::")[0]
                if any(c in written for c in "{}<>*$"):
                    continue
                written = written.rstrip("/.")
                yield path, number, written, ROOT / written


def test_every_link_and_backticked_path_resolves():
    missing = []
    for path, number, written, target in _references():
        if written in EXAMPLE_PATHS or _in_unchecked_submodule(target):
            continue
        if not target.exists():
            missing.append(f"{_rel(path)}:{number} -> {written}")
    assert not missing, (
        "these links and paths name nothing in the tree; repair them, or name "
        f"a path that is an example in EXAMPLE_PATHS with the reason: {missing}")


def test_paths_into_the_submodules_resolve():
    checked, deferred, missing = 0, 0, []
    for path, number, written, target in _references():
        try:
            parts = target.resolve().relative_to(ROOT.resolve()).parts
        except ValueError:
            continue
        if not parts or parts[0] not in SUBMODULES:
            continue
        if _in_unchecked_submodule(target):
            deferred += 1
            continue
        checked += 1
        if not target.exists():
            missing.append(f"{_rel(path)}:{number} -> {written}")
    if not checked:
        pytest.skip(f"{deferred} references into submodules that are not "
                    f"checked out here (CI checks out none)")
    assert not missing, f"these paths name nothing in their submodule: {missing}"


def test_example_paths_are_still_absent():
    """An allowance for a path that has since appeared is a stale exemption."""
    present = sorted(p for p in EXAMPLE_PATHS
                     if p != "web/dist" and (ROOT / p).exists())
    assert not present, f"EXAMPLE_PATHS exempts paths that exist: {present}"


# ── Commands ─────────────────────────────────────────────────────────────────

COMMAND = re.compile(r"(?:^|(?<=[\s`(]))(?:\$\s+)?(?:uv run\s+)?codecarto(?=\s|$)(.*)")
COMMAND_END = re.compile(r"\s#|\||>|&&|;|`")


def _command_mentions():
    """(document, line, tokens) for every `codecarto ...` a document writes:
    in a fenced block at the start of a line, in an inline code span, or after
    `uv run` anywhere. A fenced line ending in a backslash continues."""
    for path in DOCUMENTS:
        carried = ""
        for number, line, fenced in _prose_lines(path):
            if fenced:
                line = carried + line
                if line.rstrip().endswith("\\"):
                    carried = line.rstrip()[:-1] + " "
                    continue
                carried = ""
                found = COMMAND.match(line.strip())
                candidates = [found.group(1)] if found else []
            else:
                candidates = []
                for span in CODE_SPAN.findall(line):
                    found = COMMAND.match(span.strip())
                    if found:
                        candidates.append(found.group(1))
                outside = CODE_SPAN.sub(" ", line)
                candidates += re.findall(r"uv run\s+codecarto(?=\s|$)([^`]*)", outside)
            for rest in candidates:
                rest = COMMAND_END.split(rest)[0]
                yield path, number, rest.split()


def _placeholder(token: str) -> bool:
    return token.isupper() or token.startswith("<") or token in {"...", "."} \
        or "/" in token or token.startswith(("~", "$"))


def _check_command(tokens: list[str]) -> str | None:
    """None when the click tree has every command and option written."""
    from codecarto.cli import cli

    command, path = cli, ["codecarto"]
    value_for = None
    for raw in tokens:
        token = raw.strip("[]")
        if token.endswith("...") and token != "...":
            token = token[:-3].strip("[]")
        if not token:
            continue
        if value_for is not None:
            choices = getattr(value_for.type, "choices", None)
            if choices and not _placeholder(token) and token not in choices:
                return (f"{' '.join(path)} {value_for.opts[0]} {token}: not one of "
                        f"{list(choices)}")
            value_for = None
            continue
        if token.startswith("-"):
            name, _, inline = token.partition("=")
            if name == "--help":
                continue
            option = next((p for p in command.params if isinstance(p, click.Option)
                           and name in (*p.opts, *p.secondary_opts)), None)
            if option is None:
                return f"{' '.join(path)} has no option {name}"
            if not (option.is_flag or option.count) and not inline:
                value_for = option
            continue
        if isinstance(command, click.Group):
            if token in command.commands:
                command = command.commands[token]
                path.append(token)
                continue
            if _placeholder(token):
                return None
            return f"{' '.join(path)} has no command {token}"
    return None


def test_every_documented_command_exists():
    wrong = []
    for path, number, tokens in _command_mentions():
        problem = _check_command(tokens)
        if problem:
            wrong.append(f"{_rel(path)}:{number}: {problem}")
    assert not wrong, f"documents write commands the CLI does not have: {wrong}"


def test_the_command_reader_sees_commands():
    """The reader finds the commands it is meant to read, so a green result
    is not an empty one."""
    seen = {" ".join(t[:2]) for _, _, t in _command_mentions()}
    assert {"repo graph", "cargo record", "serve --help"} <= seen, seen


# ── The response envelope ────────────────────────────────────────────────────

ENVELOPE = {"status", "message", "results"}
NOT_ENVELOPE = {"code", "data"}


def _top_level_keys(block: str) -> set[str]:
    keys, depth, i = set(), 0, 0
    while i < len(block):
        c = block[i]
        if c == '"':
            end = block.index('"', i + 1)
            if depth == 1 and re.match(r"\s*:", block[end + 1:]):
                keys.add(block[i + 1:end])
            i = end + 1
            continue
        depth += {"{": 1, "[": 1, "}": -1, "]": -1}.get(c, 0)
        i += 1
    return keys


def _json_blocks(path: Path):
    block, start, inside = [], 0, False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not inside and line.strip() == "```json":
            inside, start, block = True, number, []
        elif inside and line.strip().startswith("```"):
            inside = False
            yield start, "\n".join(block)
        elif inside:
            block.append(line)


def test_api_reference_envelopes_are_the_ones_routes_return():
    """`generate_return` answers `{status, message, results}`."""
    api = ROOT / "docs" / "api.md"
    wrong, envelopes = [], 0
    for start, block in _json_blocks(api):
        keys = _top_level_keys(block)
        if not keys & (ENVELOPE | NOT_ENVELOPE) - {"message"}:
            continue
        envelopes += 1
        if keys & NOT_ENVELOPE or not ENVELOPE <= keys:
            wrong.append(f"docs/api.md:{start}: {sorted(keys)}")
    assert envelopes, "no envelope sample found in docs/api.md; the reader is stale"
    assert not wrong, (
        f"these samples are not the {sorted(ENVELOPE)} envelope "
        f"(codecarto/util/utilities.py generate_return): {wrong}")


# ── Environment variables ────────────────────────────────────────────────────

# Read by the code, set by a toolchain rather than by a person running this.
TOOLCHAIN_VARIABLES = {"CI": "set by CI runners; read by web/playwright.config.ts"}

PY_ENV = re.compile(
    r"(?:environ\.get|getenv|environ\.setdefault)\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"
    r"|environ\[\s*[\"']([A-Z][A-Z0-9_]*)[\"']\s*\]"
    r"|^\s*[A-Z_]*ENV[A-Z_]*\s*=\s*[\"']([A-Z][A-Z0-9_]*)[\"']", re.M)
JS_ENV = re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]*)|\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\])")
OURS = re.compile(r"\b(?:CODECARTO|CC)_[A-Z0-9_]+\b")


def _variables_read() -> set[str]:
    found = set()
    for source in (ROOT / "codecarto").rglob("*.py"):
        for groups in PY_ENV.findall(source.read_text(encoding="utf-8")):
            found.update(g for g in groups if g)
    web = ROOT / "web"
    for source in [*web.glob("*.js"), *web.glob("*.ts"), *web.glob("*.mjs"),
                   *(web / "src").rglob("*.ts")]:
        for groups in JS_ENV.findall(source.read_text(encoding="utf-8")):
            found.update(g for g in groups if g)
    return found


def _variables_in_cli_table() -> set[str]:
    cli_md = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
    section = re.search(r"^## Environment Variables\n(.*?)(?=^## |\Z)", cli_md, re.M | re.S)
    assert section, "docs/cli.md has no '## Environment Variables' section"
    return set(re.findall(r"^\|\s*`([A-Z][A-Z0-9_]*)`", section.group(1), re.M))


def test_every_variable_the_code_reads_is_in_the_cli_reference():
    read = _variables_read()
    assert {"CODECARTO_PORT", "CODECARTO_WEB_PORT", "MONGODB_URI"} <= read, (
        f"the reader found {sorted(read)}; its patterns are stale")
    missing = sorted(read - _variables_in_cli_table() - set(TOOLCHAIN_VARIABLES))
    assert not missing, (
        f"the code reads these and docs/cli.md's Environment Variables table "
        f"does not name them: {missing}")


def test_every_variable_a_document_names_is_read_by_the_code():
    read = _variables_read()
    stale = sorted(f"docs/cli.md: {v}" for v in _variables_in_cli_table() - read)
    for path in DOCUMENTS:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stale += [f"{_rel(path)}:{number}: {v}" for v in OURS.findall(line)
                      if v not in read]
    assert not stale, f"documents name variables nothing reads: {stale}"


# ── The environment ──────────────────────────────────────────────────────────

# The environment is uv.lock with both extras. A sync without `--locked` may
# rewrite the lockfile; one without `dev` uninstalls pytest and ruff; one
# without `c-parsing` uninstalls libclang, after which C files draw empty.
ONE_SYNC = "uv sync --locked --extra dev --extra c-parsing"
SYNC = re.compile(r"\buv\s+sync\b([^`\"'#|;)\n]*)")
CODE = ("codecarto", "scripts", "tests", "web")


def _code_files() -> list[Path]:
    """Every tracked file under `CODE`; outside a git checkout, every file
    there that is not a dependency, a build or a cache."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "--", *CODE], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout
        return sorted(ROOT / name for name in listing.splitlines())
    except (OSError, subprocess.CalledProcessError):
        skip = {"node_modules", "dist", "dist-pure", "__pycache__"}
        return sorted(p for d in CODE for p in (ROOT / d).rglob("*")
                      if p.is_file() and not skip & set(p.relative_to(ROOT).parts))


def _sync_hints():
    """(file, line, what follows the command) for every sync a document or
    the code tells a reader to run, fenced or not."""
    for path in [*DOCUMENTS, *_code_files()]:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for written in SYNC.findall(line):
                yield path, number, written


def _missing_from_the_one_sync(written: str) -> list[str]:
    tokens = written.split()
    extras = {tokens[i + 1] for i, t in enumerate(tokens[:-1]) if t == "--extra"}
    extras |= {t.split("=", 1)[1] for t in tokens if t.startswith("--extra=")}
    missing = [] if "--locked" in tokens else ["--locked"]
    return missing + [f"--extra {e}" for e in ("dev", "c-parsing") if e not in extras]


def test_every_sync_a_reader_is_told_to_run_is_the_one_sync():
    hints = list(_sync_hints())
    assert {"codecarto/cli.py", "docs/cli.md"} <= {_rel(p) for p, _, _ in hints}, (
        "the reader found no sync in the lint hint or its document; its pattern is stale")
    wrong = [f"{_rel(path)}:{number}: lacks {', '.join(missing)}"
             for path, number, written in hints
             if (missing := _missing_from_the_one_sync(written))]
    assert not wrong, (
        f"a reader who runs these leaves the environment short of the lockfile; "
        f"each is to be `{ONE_SYNC}`: {wrong}")


# ── The index ────────────────────────────────────────────────────────────────


def test_the_docs_index_links_every_page_under_docs():
    index = ROOT / "docs" / "index.md"
    linked = set()
    for _, line, fenced in _prose_lines(index):
        for target in LINK.findall(line):
            if not re.match(r"^(?:[a-z][a-z0-9+.-]*:|#)", target):
                linked.add((index.parent / target.split("#")[0]).resolve())
    pages = [p for p in DOCUMENTS
             if _rel(p).startswith("docs/") and p != index]
    missing = sorted(_rel(p) for p in pages if p.resolve() not in linked)
    assert not missing, f"docs/index.md does not link: {missing}"


# ── The web application ──────────────────────────────────────────────────────


def test_ui_reference_names_every_registered_panel():
    """The panel table in the UI reference is a reading of `panel_registry.ts`."""
    registry = (ROOT / "web" / "src" / "layout" / "panel_registry.ts").read_text(encoding="utf-8")
    ids = set(re.findall(r"^\s+id: '([a-z-]+)',", registry, re.M))
    assert ids, "no panel ids found in panel_registry.ts; the pattern is stale"
    reference = (ROOT / "docs" / "ui.md").read_text(encoding="utf-8")
    missing = sorted(i for i in ids if f"`{i}`" not in reference)
    assert not missing, f"docs/ui.md's panel table lacks: {missing}"


def test_no_source_directory_is_shadowed_by_the_dev_proxy(prefixes):
    """A top-level `web/src/<name>/` named like an API prefix never loads.

    Vite serves the source tree from `web/src`, so a module under
    `web/src/estate/` is requested as `/estate/...`, which the dev server
    proxies to the backend, which answers 404. Modules live under `features/`.
    """
    src = ROOT / "web" / "src"
    shadowed = sorted(
        f"web/src/{p.name}" for p in src.iterdir()
        if p.is_dir() and f"/{p.name}" in prefixes)
    assert not shadowed, (
        f"these source directories share a name with an API prefix in "
        f"API_PATHS, so the dev server proxies their modules to the backend: "
        f"{shadowed}")


def test_every_default_layout_entry_carries_its_registry_id():
    """`findFirstComponentItemById` is how a panel is focused or re-opened.

    A default-layout entry without an `id` is invisible to it. Every
    `componentType` in the default layout must be followed by an `id` equal
    to it.
    """
    layout = (ROOT / "web" / "src" / "layout" / "default_layout.ts").read_text(encoding="utf-8")
    entries = re.findall(r"componentType: '([a-z-]+)',\s*\n\s*title: '[^']*',\s*\n\s*(id: '([a-z-]+)',)?", layout)
    assert entries, "no component entries found in default_layout.ts; the pattern is stale"
    wrong = [f"{kind} -> {ident or 'no id'}" for kind, _, ident in entries if ident != kind]
    assert not wrong, f"default layout entries whose id is missing or differs from the type: {wrong}"


def test_the_api_reference_says_the_errors_the_envelope_does_not_carry():
    """A path no route serves is FastAPI's own 404 and a request that fails
    validation its 422; neither passes through `http_exception_handler`, so
    neither answers `{message}`. Mutation: drop the 422 row, or the unknown
    route's body, from `docs/api.md` -- this fails naming it."""
    from fastapi.testclient import TestClient

    from codecarto.main import app

    client = TestClient(app)
    unknown = client.get("/no/such/route")
    invalid = client.post("/parse/unified", json={})
    reference = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    assert unknown.status_code == 404 and unknown.json() == {"detail": "Not Found"}
    assert invalid.status_code == 422 and isinstance(invalid.json().get("detail"), list)
    assert '{"detail": "Not Found"}' in reference, "api.md does not show an unknown route's 404"
    assert re.search(r"^\| 422 \|", reference, re.M), "api.md's error table has no 422 row"


# ── Statements the code can hold ─────────────────────────────────────────────


def _paragraphs(path: Path):
    """(first line, text) for each prose paragraph of a document, its lines
    joined. A heading, a table row and a list item each start one; a table
    row and a heading are one line. Fenced blocks are not prose."""
    para, start = [], 0
    for number, line, fenced in _prose_lines(path):
        text = line.strip()
        opens = text.startswith(("|", "#")) or re.match(r"(?:[-*+]|\d+\.)\s", text)
        if (fenced or not text or opens) and para:
            yield start, " ".join(para)
            para = []
        if fenced or not text:
            continue
        if text.startswith(("|", "#")):
            yield number, text
            continue
        if not para:
            start = number
        para.append(text)
    if para:
        yield start, " ".join(para)


GRAPH_KEY_PARTS = re.compile(r"\burl\W+mode\W+layout\W+(?:and\W+)?extensions\b", re.I)
SCHEMA_VERSION = re.compile(r"schema version|GRAPH_SCHEMA_VERSION", re.I)


def test_every_statement_of_the_graph_cache_key_names_the_schema_version(monkeypatch):
    """`cache_service._make_key` hashes `v{GRAPH_SCHEMA_VERSION}` with the url,
    mode, layout and extensions, so a graph cached in an older shape is a
    miss. A sentence giving the key as those four alone tells a reader that an
    old graph is replayed. Mutation: drop the version from a statement, or from
    `_make_key`'s payload -- this fails naming it."""
    from codecarto.services import cache_service

    parts = ["https://github.com/o/r", "full", "Spring", [".py"]]
    key = cache_service._make_key(*parts)
    for i, other in enumerate(["https://github.com/o/s", "c", "Circular", [".c"]]):
        changed = [*parts[:i], other, *parts[i + 1:]]
        assert cache_service._make_key(*changed) != key, (
            f"_make_key no longer varies on its {['url', 'mode', 'layout', 'extensions'][i]}")
    monkeypatch.setattr(cache_service, "GRAPH_SCHEMA_VERSION",
                        cache_service.GRAPH_SCHEMA_VERSION + 1)
    assert cache_service._make_key(*parts) != key, (
        "the graph key no longer carries GRAPH_SCHEMA_VERSION; the statements "
        "this reads are stale, and so is this check")

    seen, wrong = 0, []
    for path in DOCUMENTS:
        for number, text in _paragraphs(path):
            for match in GRAPH_KEY_PARTS.finditer(text):
                if re.search(r"\b(?:cache_key|_make_key)\($", text[:match.start()]):
                    continue  # the function's signature: the version is not an argument
                seen += 1
                window = text[max(0, match.start() - 120):match.end() + 120]
                if not SCHEMA_VERSION.search(window):
                    wrong.append(f"{_rel(path)}:{number}: {match.group(0)}")
    assert seen, "no document states the graph cache key; the reader is stale"
    assert not wrong, (
        f"these give the graph cache key without the schema version "
        f"(`v{{GRAPH_SCHEMA_VERSION}}`, cache_service._make_key): {wrong}")


def _section(path: Path, heading: str) -> list[tuple[int, str]]:
    """The paragraphs under `## heading`, to the next heading of that level."""
    found, inside = [], False
    for number, text in _paragraphs(path):
        if text.startswith("## "):
            inside = text == f"## {heading}"
            continue
        if inside:
            found.append((number, text))
    return found


def test_the_caches_section_says_evicting_one_cache_empties_the_other(monkeypatch, tmp_path):
    """For a GitHub repository both caches are one directory,
    `~/.codecarto/cache/repos/{owner}-{repo}/`, and each eviction that removes
    a repository removes it whole: `DELETE /c-parser/cache/{key}` takes Cache
    A's tree and graphs and leaves their `index.json` entries, and
    `CacheService.evict_repo` takes Cache B's source. Mutation: drop the
    paragraph from architecture.md, or give the caches separate directories
    or the C eviction the index -- this fails, and the paragraph is to say what
    the code then does."""
    from codecarto.services import c_parser_service, cache_service
    from codecarto.services.c_parser_service import CParserService
    from codecarto.services.cache_service import CacheService

    assert cache_service._REPOS_DIR == c_parser_service._REPO_CACHE_DIR, (
        "the two caches no longer share a directory; the paragraph is stale")
    repos = tmp_path / "repos"
    monkeypatch.setattr(cache_service, "_REPOS_DIR", repos)
    monkeypatch.setattr(cache_service, "_INDEX_FILE", repos / "index.json")
    monkeypatch.setattr(cache_service, "_mongo_col", lambda: None)
    monkeypatch.setattr(c_parser_service, "_REPO_CACHE_DIR", repos)

    url = "https://github.com/o/r"
    key = CacheService.cache_key(url, "2", "Spring", [])

    def fill():
        CacheService.set_tree(url, {"tree": True})
        CacheService.set(key, {"graph": {}}, label="o/r", url=url)
        (repos / "o-r" / "src").mkdir(parents=True, exist_ok=True)
        (repos / "o-r" / "metadata.json").write_text("{}")

    fill()
    assert CParserService.evict_repo_cache("o-r")
    assert CacheService.get_tree(url) is None and CacheService.get(key) is None, (
        "DELETE /c-parser/cache/{key} no longer removes Cache A's tree and graphs")
    assert key in {e["key"] for e in CacheService.list_cached()}, (
        "DELETE /c-parser/cache/{key} now drops the index entries it orphans")
    fill()
    assert CacheService.evict_repo(url)
    assert not (repos / "o-r" / "src").exists(), (
        "CacheService.evict_repo no longer removes Cache B's source")

    paragraphs = [text for _, text in _section(
        ROOT / "docs" / "architecture.md", "The two caches") if not text.startswith("|")]
    stated = [t for t in paragraphs if "DELETE /c-parser/cache/{key}" in t
              and "index.json" in t and "evict_repo" in t]
    assert stated, (
        "docs/architecture.md, *The two caches*, does not say that evicting a "
        "GitHub repository from one cache removes the other's directory too, "
        "and leaves index.json naming graphs that are gone")


def test_c_edge_kinds_are_named_as_the_graph_that_carries_them():
    """`CParser` writes its edge kinds in upper case (`CALLS`, `FIELD_OF`);
    `/c-parser/*` answers them so, and `c_language_parser._EDGE_KIND_MAP`
    turns them into what a `/parse/*` graph carries (`calls`, `field_of`, and
    `contains` for `LOCAL_OF`). A paragraph naming an upper-case kind is about
    `/c-parser/*`, and a lower-case spelling of one is a kind the map gives.
    Mutation: write `CALLS` into a paragraph about `/parse/*`, or `local_of`
    anywhere -- this fails naming it."""
    from codecarto.services.parsers.c_language_parser import _EDGE_KIND_MAP

    assert all(k.isupper() for k in _EDGE_KIND_MAP), _EDGE_KIND_MAP
    assert all(v.islower() for v in _EDGE_KIND_MAP.values()), _EDGE_KIND_MAP
    upper = set(_EDGE_KIND_MAP)
    spelled = {k.lower() for k in upper}
    given = set(_EDGE_KIND_MAP.values())
    wrong = []
    for path in DOCUMENTS:
        for number, text in _paragraphs(path):
            spans = {s.strip() for s in CODE_SPAN.findall(text)}
            if spans & upper and "/c-parser" not in text:
                wrong.append(f"{_rel(path)}:{number}: {sorted(spans & upper)} "
                             f"outside /c-parser/*")
            if (spans & spelled) - given:
                wrong.append(f"{_rel(path)}:{number}: {sorted((spans & spelled) - given)} "
                             f"is no kind _EDGE_KIND_MAP gives")
    assert not wrong, (
        f"a /parse/* graph's C edges are {sorted(given)} "
        f"(c_language_parser._EDGE_KIND_MAP); the upper-case kinds are "
        f"/c-parser/*'s: {wrong}")


def _depth_rows(depth: int):
    """(document, line, the row's other cells) for the row of `depth` in every
    table whose first header cell is `depth`."""
    for path in DOCUMENTS:
        header = None
        for number, line, fenced in _prose_lines(path):
            text = line.strip()
            if fenced or not text.startswith("|"):
                header = None
                continue
            cells = [c.strip() for c in text.strip("|").split("|")]
            if header is None:
                header = cells
            elif header[0] == "depth" and cells[0] == str(depth):
                yield path, number, " ".join(cells[1:])


def test_every_depth_table_names_what_the_c_parser_puts_at_depth_3():
    """`CLangaugeParser._convert` puts a struct's fields, an enum's constants and
    a function's locals (a `LOCAL_OF` target) at depth 3. Each depth table's
    row 3 names the three, so a reader asking for depth 3 knows a C function
    brings its locals. Mutation: drop "locals" from a row -- this fails."""
    from codecarto.services.parsers.c_language_parser import CLangaugeParser

    def node(nid, kind):
        return {"id": nid, "kind": kind, "name": nid, "file": "a", "line": 1}

    raw = {"nodes": [node("f", "function"), node("f::x", "variable"),
                     node("struct s", "struct"), node("struct s::a", "field"),
                     node("enum e", "enum"), node("enum e::A", "enum_constant")],
           "edges": [{"src": "f", "dst": "f::x", "kind": "LOCAL_OF"},
                     {"src": "struct s", "dst": "struct s::a", "kind": "FIELD_OF"}]}
    graph = CLangaugeParser()._convert(raw, 3)
    kinds = {a["kind"] for _, a in graph.nodes(data=True) if a["depth"] == 3}
    assert kinds == {"variable", "field", "enum_constant"}, kinds
    # A variable reaches depth 3 only as a function's local.
    words = {"local" if k == "variable" else k.replace("_", " ") for k in kinds}

    rows, wrong = 0, []
    for path, number, row in _depth_rows(3):
        rows += 1
        missing = sorted(w for w in words if not re.search(rf"\b{w}s?\b", row, re.I))
        if missing:
            wrong.append(f"{_rel(path)}:{number}: lacks {missing}")
    assert rows >= 2, "the reader found fewer depth tables than api.md and architecture.md hold"
    assert not wrong, f"these depth-3 rows do not name what C puts there: {wrong}"
