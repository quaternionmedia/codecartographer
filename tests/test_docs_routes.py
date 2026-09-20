"""The documents say what the application says.

**A ROUTE TABLE IN PROSE IS A CLAIM WITH AN EXPIRY DATE**, and this project's
had expired three ways at once: `docs/api.md` documented no route under
`/topology`, `/capabilities` or `/overview` while the application served all
three; the dev server's proxy list left two of them out, so a request to either
was one the dev server tried to answer itself and could not; and five documents
named a port this project stopped binding when it took the constant the
dashboard allocates. Nothing was red.

So the application is the source here and the documents are read against it:
every prefix `codecarto.main.app` mounts must appear in the README's table, in
`docs/api.md` under a heading, and in `web/vite.config.js`'s `API_PATHS`; and
no document may name the port this project no longer binds.

**READ FROM THE TREE, NOT FROM A LIST HERE.** A list of prefixes in this file
would be a fourth copy to go stale. The prefixes come from the app's own routes,
the port from `codecarto.cli.DEFAULT_PORT`.

Seen red before trusted: run against the tree before the documents were
repaired, this file failed on all three route checks and on the port check;
each was then repaired and the check went green.

WHAT THIS CANNOT SEE. Whether the documented *description* of a route is right.
It checks presence, which is the failure that actually happened, and not
meaning.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Served by the application and not documented as API: FastAPI's own pages,
# the built web application and its assets, and the root redirect.
NOT_API = {"", "app", "assets", "docs", "redoc", "openapi.json"}

# Documents a reader is sent to. History and the legacy archive are stamped
# records of what was, and are not read against the tree.
DOCUMENTS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    *sorted((ROOT / "docs").glob("*.md")),
    *sorted((ROOT / "docs" / "llm").glob("*.md")),
    *sorted((ROOT / "docs" / "llm" / "roadmap").glob("*.md")),
]


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


def test_readme_table_names_every_mounted_prefix(prefixes):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = sorted(p for p in prefixes if f"| `{p}` |" not in readme)
    assert not missing, f"README.md's API table lacks a row for: {missing}"


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
                stale.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    assert not stale, (
        f"these lines name :{retired}, which this project stopped binding; "
        f"the constant is codecarto.cli.DEFAULT_PORT and `serve --help` prints "
        f"it: {stale}")


def test_documents_do_not_restate_the_test_count():
    """A test count in prose is stale the next time somebody adds a test.

    The command is what a reader needs; the figure is what the command prints.
    """
    offenders = []
    for path in (ROOT / "README.md", ROOT / "AGENTS.md"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\b\d{3,}\s+tests\b", line):
                offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert not offenders, f"a test count in durable text: {offenders}"


def test_ui_reference_names_every_registered_panel():
    """The panel table in the UI reference is a reading of `panel_registry.ts`.

    It once described three panels while the registry held eight, and named a
    Restore button the add-window menu had replaced.
    """
    registry = (ROOT / "web" / "src" / "layout" / "panel_registry.ts").read_text(encoding="utf-8")
    ids = set(re.findall(r"^\s+id: '([a-z-]+)',", registry, re.M))
    assert ids, "no panel ids found in panel_registry.ts; the pattern is stale"
    reference = (ROOT / "docs" / "llm" / "UI_REFERENCE.md").read_text(encoding="utf-8")
    missing = sorted(i for i in ids if f"`{i}`" not in reference)
    assert not missing, f"docs/llm/UI_REFERENCE.md's panel table lacks: {missing}"


def test_no_source_directory_is_shadowed_by_the_dev_proxy(prefixes):
    """A top-level `web/src/<name>/` named like an API prefix never loads.

    Vite serves the source tree from `web/src`, so a module under
    `web/src/estate/` is requested as `/estate/...` -- and `/estate` is a prefix
    the dev server proxies to the backend, which answers 404. The application
    then does not mount, and nothing in a unit test can see it: the first
    estate module lived at exactly that path and every browser test went red
    with a timeout waiting for a button. Modules live under `features/`, and
    this fails when a top-level source directory takes an API prefix's name.
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

    A default-layout entry without an `id` is invisible to it: the canvas could
    not be brought to the front after a draw, and re-opening it would have
    added a second one. Every `componentType` in the default layout must be
    followed by an `id` equal to it.
    """
    layout = (ROOT / "web" / "src" / "layout" / "default_layout.ts").read_text(encoding="utf-8")
    entries = re.findall(r"componentType: '([a-z-]+)',\s*\n\s*title: '[^']*',\s*\n\s*(id: '([a-z-]+)',)?", layout)
    assert entries, "no component entries found in default_layout.ts; the pattern is stale"
    wrong = [f"{kind} -> {ident or 'no id'}" for kind, _, ident in entries if ident != kind]
    assert not wrong, f"default layout entries whose id is missing or differs from the type: {wrong}"
