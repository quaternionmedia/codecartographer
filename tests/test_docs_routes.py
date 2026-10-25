"""The documents say what the application says.

Every tracked Markdown file outside the two submodules is read against the tree
it describes, and each check here fails on a document that disagrees with it:

- every prefix `codecarto.main.app` mounts appears in `docs/api.md`'s overview
  table and under one of its headings, and in `web/vite.config.js`'s
  `API_PATHS`;
- the README is an onramp: at most `README_LINES` lines;
- no document names the port this project no longer binds, or a test count;
- every relative link resolves, and so does every repository path written in
  backticks in prose, unless `EXAMPLE_PATHS` names it;
- every `codecarto ...` command a document writes exists in the click tree,
  with its options, and a value from a fixed choice is one of the choices;
- every JSON envelope in `docs/api.md` has `status`, `message` and `results`;
- every environment variable the code reads is in `docs/cli.md`'s table, and
  every one a document names is read by the code;
- `docs/index.md` links every page under `docs/`;
- the UI reference names every registered panel; under each radial ring, every
  item that ring builds and no other; and the keys and the hold that open and
  move a ring, as the code binds them;
- the default layout and the source tree agree with the registry and the dev
  proxy.

The application, the click tree and the code are the sources; nothing here
keeps a list of routes, commands or variables of its own.

WHAT THIS CANNOT SEE. Whether a description is right: it checks that what a
document names exists, not that the sentence about it is true. Paths into a
submodule are checked only where the submodule is checked out, which CI does
not do.
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


def test_dev_server_proxies_every_mounted_prefix(prefixes):
    """A prefix absent from `API_PATHS` is a request Vite answers itself."""
    config = (ROOT / "web" / "vite.config.js").read_text(encoding="utf-8")
    block = re.search(r"const API_PATHS = \[(.*?)\];", config, re.S)
    assert block, "web/vite.config.js has no API_PATHS list"
    listed = set(re.findall(r"'(/[^']*)'", block.group(1)))
    missing = sorted(p for p in prefixes if p not in listed)
    assert not missing, f"web/vite.config.js API_PATHS lacks: {missing}"


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


RAD = ROOT / "web" / "src" / "features" / "graph" / "rad"
BOLD = re.compile(r"\*\*([^*\n]+)\*\*")


def _ui_sections() -> dict[str, str]:
    """{heading text: body} for every heading in `docs/ui.md`; a body runs to
    the next heading of any level."""
    text = (ROOT / "docs" / "ui.md").read_text(encoding="utf-8")
    parts = re.split(r"^#{1,6} +(.+?)\s*$", text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def _labels(body: str) -> set[str]:
    """Every item label written in a stretch of `resolve.ts`: a quoted label,
    both branches of a conditional one, and the fixed words of a template."""
    found = set()
    for value in re.findall(r"\blabel:\s*([^,\n]+)", body):
        quoted = re.findall(r"'([^']+)'", value)
        if quoted:
            found.update(quoted)
            continue
        template = re.match(r"`([^`$]*)", value.strip())
        if template and template.group(1).strip():
            found.add(template.group(1).strip())
    return found


def _rings_built() -> dict[str, set[str]]:
    """{'<Name> ring': labels} for every `function <name>Ring(` in `resolve.ts`,
    and {'Color submenu': labels} for `COLOUR_RING`. A submenu written inside a
    ring's function (View) is that ring's."""
    source = (RAD / "host" / "resolve.ts").read_text(encoding="utf-8")
    rings = {f"{name.capitalize()} ring": _labels(body) for name, body in re.findall(
        r"^function (\w+)Ring\([^)]*\)[^{]*\{(.*?)^\}", source, re.M | re.S)}
    colour = re.search(r"^const COLOUR_RING\b[^=]*=\s*\[(.*?)^\];", source, re.M | re.S)
    if colour:
        rings["Color submenu"] = _labels(colour.group(1))
    return rings


def test_ui_reference_names_every_ring_item_and_no_other():
    """Each ring `resolve.ts` builds has a `### <Name> ring` section in the UI
    reference, and the items it offers are the bold words in that section: all
    of them, and nothing the code does not build. A section for a ring the code
    does not build is a ring the reader cannot open."""
    rings = _rings_built()
    assert rings and all(rings.values()), (
        f"read {rings} from resolve.ts; the ring or label pattern is stale")
    sections = {name: body for name, body in _ui_sections().items()
                if re.fullmatch(r"\w+ ring|\w+ submenu", name)}
    wrong = [f"no section '### {name}'" for name in sorted(set(rings) - set(sections))]
    wrong += [f"'### {name}' names a ring resolve.ts does not build"
              for name in sorted(set(sections) - set(rings))]
    for name in sorted(set(rings) & set(sections)):
        named = set(BOLD.findall(sections[name]))
        if rings[name] - named:
            wrong.append(f"{name} lacks {sorted(rings[name] - named)}")
        if named - rings[name]:
            wrong.append(f"{name} names {sorted(named - rings[name])}, which it does not build")
    assert not wrong, f"docs/ui.md and resolve.ts disagree about the radial menu: {wrong}"


def test_ui_reference_names_the_keys_and_the_hold_that_work_a_ring():
    """The keys `attach.ts` binds -- the one that opens a ring and the ones
    that move inside it -- are the keys in backticks under `### Opening a ring`
    and `### Keys in a ring`, and the hold that opens one is the time
    `geometry.ts` sets."""
    attach = (RAD / "dom" / "attach.ts").read_text(encoding="utf-8")
    inside = re.search(r"\[([^\]]*)\]\.includes\(ev\.key\)", attach)
    opening = re.findall(r"ev\.key === '([^']+)'", attach)
    hold = re.search(r"\blongPressMs:\s*(\d+)",
                     (RAD / "core" / "geometry.ts").read_text(encoding="utf-8"))
    assert inside and opening and hold, (
        "attach.ts or geometry.ts no longer reads as expected; the key or hold pattern is stale")
    bound = set(re.findall(r"'([^']+)'", inside.group(1))) | set(opening)

    sections = _ui_sections()
    assert {"Opening a ring", "Keys in a ring"} <= set(sections), (
        "docs/ui.md has no '### Opening a ring' or '### Keys in a ring'")
    named = set(CODE_SPAN.findall(sections["Opening a ring"] + sections["Keys in a ring"]))
    assert named == bound, (
        f"docs/ui.md names keys {sorted(named)}; attach.ts binds {sorted(bound)}")
    assert f"{hold.group(1)} ms" in sections["Opening a ring"], (
        f"geometry.ts holds for {hold.group(1)} ms; '### Opening a ring' does not say so")


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
