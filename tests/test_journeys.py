"""The journeys `docs/journeys.md` writes are the ones the page's browser tests walk.

Each of the page's journeys ends ``Walked by `journey: ...` ``, the title of a
test in `web/tests/e2e/view.spec.ts`, and says where it starts and where it
arrives. Each check here fails on a page and a suite that disagree:

- a journey whose test does not exist, and a `journey:` test no journey names;
- a journey of the page that does not say where it starts and arrives, or that
  the table of where to start does not link;
- a link from the page to the window at another port or path than the one
  `codecarto serve` binds and the app router mounts.
"""

from __future__ import annotations

import re
from pathlib import Path

from codecarto.cli import DEFAULT_PORT

ROOT = Path(__file__).resolve().parents[1]
JOURNEYS = ROOT / "docs" / "journeys.md"
SPEC = ROOT / "web" / "tests" / "e2e" / "view.spec.ts"
WALK = ROOT / "web" / "src" / "features" / "view" / "view_walk.ts"
APP_ROUTER = ROOT / "codecarto" / "routers" / "app_router.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _walked() -> list[str]:
    """Each journey's test, as the page names it."""
    return re.findall(r"^Walked by `(journey: [^`]+)`\.$", _text(JOURNEYS), re.M)


def _tests() -> list[str]:
    """Each journey test's title, as the spec declares it."""
    return [m.group(2) for m in re.finditer(r"""^test\((['"])(journey: .+?)\1, async""", _text(SPEC), re.M)]


def _page_journeys() -> dict[str, str]:
    """Each journey of the page, by its heading: the text under it."""
    page = _text(JOURNEYS).split("\n## The page\n", 1)[1].split("\n## ", 1)[0]
    parts = re.split(r"^### (.+)$", page, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def _anchor(heading: str) -> str:
    """The anchor GitHub makes of a heading."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def test_every_journey_is_walked_by_a_test_of_its_name():
    missing = sorted(set(_walked()) - set(_tests()))
    assert not missing, f"docs/journeys.md names tests view.spec.ts does not have: {missing}"


def test_every_journey_test_is_a_journey_the_page_names():
    unnamed = sorted(set(_tests()) - set(_walked()))
    assert not unnamed, f"view.spec.ts walks journeys docs/journeys.md does not name: {unnamed}"
    assert len(_walked()) == len(set(_walked())), "a test walks two journeys"


def test_each_journey_of_the_page_says_where_it_starts_and_arrives_and_is_linked():
    journeys = _page_journeys()
    assert journeys, "docs/journeys.md has no journey under 'The page'"
    start = _text(JOURNEYS).split("\n## Where to start\n", 1)[1].split("\n## ", 1)[0]
    for heading, body in journeys.items():
        for said in ("**Starts at**", "**Arrives at**", "Walked by `journey: "):
            assert said in body, f"the journey {heading!r} does not say {said}"
        assert f"(#{_anchor(heading)})" in start, f"Where to start does not link the journey {heading!r}"


def test_the_page_links_the_window_where_codecarto_serve_binds_it():
    window = re.search(r"export const WINDOW_APP = '([^']+)';", _text(WALK))
    assert window, "view_walk.ts names no WINDOW_APP"
    assert window.group(1) == f"http://localhost:{DEFAULT_PORT}/app"
    assert '@AppRouter.get("/app"' in _text(APP_ROUTER)
    assert f"`http://localhost:{DEFAULT_PORT}/app`" in _text(JOURNEYS)
