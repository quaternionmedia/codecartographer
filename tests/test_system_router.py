"""The /system endpoints, and the names they refuse.

The router's one security-relevant decision is repository resolution: a name
is a single path segment looked up beside this checkout, and anything
separator-shaped is refused before any filesystem call. These tests pin the
refusals as behaviour, not as a comment.

THE MUTATION, per P16, quoted as it printed — the name pattern loosened to
`^.+$`:

    AssertionError: 'inside/../../outside' resolved outside the sibling roots
    AssertionError: 'inside\\..\\..\\outside' resolved outside the sibling roots

**IT TOOK THREE VERSIONS OF THESE TESTS TO MAKE THAT MUTATION FIRE**, and both
failed versions passed green:

  1. Traversal names like '../qm' whose targets did not exist on the test
     machine — the refusal was the filesystem's shape, not the guard's.
  2. Targets built for real, but every traversal name dot-prefixed — and the
     guard is doubled (`NAME`'s first-character class AND `startswith('.')`),
     so mutating `NAME` alone changed nothing any test could see.

The names that finally proved the guard are non-dot traversals aimed at a git
repository that genuinely exists outside the root. A refusal test is evidence
only when the thing refused would otherwise have succeeded.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.routers import system_router


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def escape_layout(tmp_path, monkeypatch):
    """A root with one legitimate clone inside and one git repo OUTSIDE it,
    reachable only by traversal. The first version of these tests used names
    like '../qm' whose targets did not exist on the test machine, so loosening
    the NAME pattern to `^.+$` still passed all of them — the refusal was
    being proven by the filesystem's shape, not by the guard."""
    root = tmp_path / "root"
    (root / "inside" / ".git").mkdir(parents=True)
    (tmp_path / "outside" / ".git").mkdir(parents=True)
    monkeypatch.setattr(system_router, "_roots", lambda: [root])
    return root


def test_a_legitimate_sibling_resolves(escape_layout):
    found = system_router.find_repo("inside")
    assert found is not None and found.name == "inside"


@pytest.mark.parametrize("name", [
    # Dot-prefixed: refused by NAME's first-character class AND by the
    # explicit startswith('.') — a doubled defence, so a mutation of either
    # alone is caught only by the names below.
    "../outside", "..\\outside", ".", "..", "", ".git", ".hidden", "a b",
    # NOT dot-prefixed: these get past startswith('.') and are refused only
    # by the separator ban in NAME. `inside/../../outside` resolves to a real
    # git repo in this layout, so a loosened NAME returns a Path here and the
    # test goes red — which is what showed the first version of this file was
    # passing on the filesystem's shape rather than on the guard.
    "inside/../../outside", "inside\\..\\..\\outside", "a/b", "a\\b",
])
def test_a_separator_shaped_name_is_refused_even_when_its_target_exists(
        name, escape_layout):
    assert system_router.find_repo(name) is None, (
        f"{name!r} resolved outside the sibling roots")


def test_an_unknown_repo_is_a_404_with_the_name_in_it(client):
    reply = client.get("/system/compose", params={"repo": "no-such-repo"})
    assert reply.status_code == 404
    assert "no-such-repo" in reply.json()["error"]


def test_repos_lists_only_git_clones(client):
    reply = client.get("/system/repos")
    assert reply.status_code == 200
    names = [r["name"] for r in reply.json()["repos"]]
    # This checkout's own repository is a sibling of itself in neither root,
    # but whatever is listed must at least be unique and non-hidden.
    assert len(names) == len(set(names))
    assert not any(n.startswith(".") for n in names)


def test_compose_answers_for_a_real_sibling_when_one_exists(client):
    """Runs against whatever clone actually sits beside this checkout; skips
    with the reason on a machine with none, rather than faking a sibling —
    the resolution rule (parents of THIS file) is exactly what is under test,
    and a fixture repo cannot sit there."""
    listed = client.get("/system/repos").json()["repos"]
    if not listed:
        pytest.skip("no sibling clones beside this checkout")
    name = listed[0]["name"]
    doc = client.get("/system/compose", params={"repo": name}).json()
    assert doc["system"] == name
    assert "components" in doc and "edges" in doc


def test_the_roots_override_replaces_rather_than_adds(tmp_path, monkeypatch):
    """Two sources of truth for 'which repositories can this read' is how an
    allowlist stops being one, so CODECARTO_REPO_ROOTS replaces the
    convention entirely."""
    import os

    (tmp_path / "only" / ".git").mkdir(parents=True)
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(tmp_path))

    roots = system_router._roots()

    assert roots == [tmp_path], "the override must replace the convention"
    assert system_router.find_repo("only") is not None


def test_the_replay_derives_its_events_off_the_event_loop(tmp_path, monkeypatch):
    """`events()` starts a git process per commit and per branch. Run inside the
    websocket handler, it froze every other route and socket until the
    derivation finished. Mutation: call `system_composer.events` directly in
    `replay` -- the loop ticks once while the derivation runs, and this fails."""
    import time

    def slow_events(clone, limit):
        time.sleep(0.3)
        return {"changes": [], "in_flight": []}

    monkeypatch.setattr(system_router, "find_repo", lambda name: tmp_path)
    monkeypatch.setattr(system_router.system_composer, "events", slow_events)

    class Socket:
        async def accept(self):
            pass

        async def send_json(self, data):
            pass

        async def close(self, code=1000, reason=None):
            pass

    async def ticks_while_replaying() -> int:
        ticks = 0
        replay = asyncio.ensure_future(system_router.replay(Socket(), repo="moat", limit=30))
        while not replay.done():
            ticks += 1
            await asyncio.sleep(0.01)
        await replay
        return ticks

    assert asyncio.run(ticks_while_replaying()) >= 10, \
        "the event loop stalled while the replay derived its events"
