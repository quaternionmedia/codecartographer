"""The derived-system endpoints: a diagram and its events, from a local clone.

The PAM router serves a *known* system whose picture is hand-drawn. This one
serves systems whose picture is **derived from a repository's own contents** by
`services/system_composer.py` — moat's homelab is the worked case — so it takes
a repository name and answers with whatever that repository declares.

Endpoints (mounted under /system in main.py):
  GET /repos                    -> the repositories this can find, and where
  GET /compose?repo=moat        -> derived components and edges
  GET /events?repo=moat         -> recent changes and in-flight branches
  WS  /ws/replay?repo=moat      -> the same changes, replayed with pacing, so
                                   the frontend's live path has a real feed

**WHERE A REPOSITORY MAY BE.** Beside this checkout, by name — the same
convention the rest of this estate uses for finding sibling clones, and the
whole of it. The name is a single path segment; anything with a separator or a
dot-prefix is refused, because "which repositories can this read" must be
answerable by listing two directories, not by reasoning about path traversal.

**WHAT THE REPLAY IS AND IS NOT.** The websocket replays the clone's history —
real changes, real components, real order — at a readable pace. It is a replay,
and it says so in every frame (`"replay": true`): a monitor that dressed
history up as a live tail would teach its reader that the homelab is busier
than it is. A genuinely live feed (cluster events, host webhooks) is a
different source with different credentials, deliberately not started here.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from codecarto.services import system_composer

SystemRouter = APIRouter()

# One path segment, nothing hidden, nothing traversal-shaped.
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Seconds between replayed changes. Slow enough to watch, fast enough that
# thirty changes finish inside a coffee.
REPLAY_PACE = 1.2


def _roots() -> list[Path]:
    """Where sibling clones live: beside this repository, and one level up.

    `CODECARTO_REPO_ROOTS` (os.pathsep-separated directories) overrides the
    convention entirely when set. It exists because a git worktree is not
    beside anything — its parents are wherever the worktree was made — and a
    session working from one would otherwise find no repositories at all.
    An override that *adds* roots was considered and rejected: two sources of
    truth for "which repositories can this read" is how an allowlist stops
    being one.
    """
    import os

    override = os.environ.get("CODECARTO_REPO_ROOTS", "")
    if override.strip():
        return [Path(part) for part in override.split(os.pathsep)
                if part.strip()]
    here = Path(__file__).resolve().parents[2]
    return [here.parent, here.parent.parent]


def find_repo(name: str) -> Path | None:
    if not NAME.match(name) or name.startswith("."):
        return None
    for root in _roots():
        candidate = root / name
        if (candidate / ".git").exists():
            return candidate
    return None


@SystemRouter.get("/repos")
def repos() -> JSONResponse:
    """Every sibling clone this could compose, so the frontend can offer a
    list instead of a text field somebody has to guess into."""
    found = []
    seen: set[str] = set()
    for root in _roots():
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.name in seen or not (child / ".git").exists():
                continue
            seen.add(child.name)
            found.append({"name": child.name, "path": str(child)})
    return JSONResponse({"repos": found})


@SystemRouter.get("/compose")
def compose(repo: str = Query(...)) -> JSONResponse:
    clone = find_repo(repo)
    if clone is None:
        return JSONResponse(
            {"error": f"no clone named {repo!r} beside this checkout"},
            status_code=404)
    return JSONResponse(system_composer.compose(clone))


@SystemRouter.get("/events")
def events(repo: str = Query(...), limit: int = Query(30, ge=1, le=200)
           ) -> JSONResponse:
    clone = find_repo(repo)
    if clone is None:
        return JSONResponse(
            {"error": f"no clone named {repo!r} beside this checkout"},
            status_code=404)
    return JSONResponse(system_composer.events(clone, limit=limit))


@SystemRouter.websocket("/ws/replay")
async def replay(ws: WebSocket, repo: str = Query(...),
                 limit: int = Query(30, ge=1, le=200)) -> None:
    """Replay the clone's recent changes, one frame per change, then the
    in-flight branches, then close. The frontend falls back to its canned
    demo when this refuses, which is the same contract the PAM feed has."""
    await ws.accept()
    clone = find_repo(repo)
    if clone is None:
        await ws.close(code=4404, reason=f"no clone named {repo!r}")
        return
    # A git process per commit and per branch: off the loop, or every other
    # route and socket waits for the derivation.
    payload = await run_in_threadpool(system_composer.events, clone, limit=limit)
    try:
        for change in payload["changes"]:
            await ws.send_json({
                "event_type": "change", "replay": True,
                "sha": change["sha"], "when": change["when"],
                "subject": change["subject"],
                "components": change["components"],
            })
            await asyncio.sleep(REPLAY_PACE)
        for branch in payload["in_flight"]:
            await ws.send_json({
                "event_type": "in_flight", "replay": True,
                "branch": branch["branch"], "commits": branch["commits"],
                "components": branch["components"],
            })
            await asyncio.sleep(REPLAY_PACE)
        await ws.send_json({"event_type": "replay_done", "replay": True})
        await ws.close()
    except (WebSocketDisconnect, RuntimeError):
        # The viewer navigated away mid-replay. Ordinary, not an error.
        return
