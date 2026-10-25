"""A route that waits on another server, or works for seconds, does not hold up the rest.

The estate and topology routes ask other servers -- the harness, the corpus's
neighbours -- and wait up to a timeout when nobody answers. The plotter routes
parse this project's own source or render a figure, which takes seconds. FastAPI
runs an `async def` route on the event loop, so a blocking call inside one
stalls every other request until it returns. These tests make the slow part
slow and check that a cheap route answers in the meantime.

Each test patches the slow part to sleep, starts the slow route, waits until
the stand-in is inside its sleep, then asks `/parse/languages`, timing both from
before the slow request. On the event loop the cheap answer cannot come back
until the sleep ends; off it, it comes back at once.
"""

from __future__ import annotations

import asyncio
import threading
import time

import gravis
import httpx
import pytest

from codecarto.main import app
from codecarto.routers import plotter_router
from codecarto.services import estate_service, qmcp_client
from codecarto.services.unified_parser_service import UnifiedParserService

SLOW = 0.8
# Generous for a loaded runner, and well under SLOW: a route held up by the
# slow one cannot answer before the sleep ends.
CHEAP_WITHIN = SLOW / 2


#: Set by a stand-in when it starts waiting, so the cheap request goes out while
#: the slow route is inside its wait rather than before it gets there.
_waiting = threading.Event()


def _slow_reach(*_args, **_kwargs) -> qmcp_client.Reach:
    _waiting.set()
    time.sleep(SLOW)
    return qmcp_client.Reach(ok=False, where="http://127.0.0.1:9", problem="slow test seam",
                             remedy="none: a test")


def _slow_survey(*_args, **_kwargs) -> list:
    _waiting.set()
    time.sleep(SLOW)
    return []


def _slow_parse(*_args, **_kwargs) -> dict:
    _waiting.set()
    time.sleep(SLOW)
    return {"graph": {"nodes": {}, "edges": []}, "metadata": {}}


class _Figure:
    def to_html_standalone(self) -> str:
        return "<html></html>"


def _slow_figure(*_args, **_kwargs) -> _Figure:
    _slow_parse()
    return _Figure()


def _nothing(*_args, **_kwargs) -> None:
    return None


async def _cheap_while(slow_path: str, body: dict | None = None) -> tuple[float, int]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        started = time.perf_counter()
        slow = asyncio.create_task(
            client.get(slow_path) if body is None else client.post(slow_path, json=body))
        # A thread waits for the stand-in, so this coroutine resumes only when
        # the event loop is free: at once off the loop, after SLOW on it.
        assert await asyncio.to_thread(_waiting.wait, 5), f"{slow_path} never reached its seam"
        cheap = await client.get("/parse/languages")
        took = time.perf_counter() - started
        assert (await slow).status_code == 200
        return took, cheap.status_code


@pytest.mark.parametrize(("slow_path", "target", "name", "stand_in"), [
    ("/estate/seams", estate_service, "survey", _slow_survey),
    ("/topology/available", qmcp_client, "topologies", _slow_reach),
    ("/topology/gjgf", qmcp_client, "shape", _slow_reach),
    ("/topology/data", qmcp_client, "shape", _slow_reach),
    # A subject asks the harness for its relations rather than a shape: the
    # other branch of `topology_router._fetch`.
    ("/topology/gjgf?subject=codecarto", qmcp_client, "relations", _slow_reach),
])
def test_a_slow_seam_does_not_hold_up_a_cheap_route(monkeypatch, slow_path, target, name, stand_in):
    monkeypatch.setattr(target, name, stand_in)
    _waiting.clear()
    took, status = asyncio.run(_cheap_while(slow_path))
    assert status == 200
    assert took < CHEAP_WITHIN, (
        f"/parse/languages took {took:.2f}s while {slow_path} waited {SLOW}s on its seam: "
        f"{slow_path} is blocking the event loop")


_DEMO = {"options": {"palette_id": "0", "layout": "Spring", "type": "d3", "parse_by": "code"}}
_RENDER = {"graph_data": {"graph": {"nodes": {}, "edges": []}}, "options": {}}


@pytest.mark.parametrize(("slow_path", "body", "patches"), [
    # The demo reads this project's source, then parses it: 8.46s measured.
    ("/plotter/demo", _DEMO, [(plotter_router, "get_local_repo", _nothing),
                              (UnifiedParserService, "parse", _slow_parse)]),
    ("/plotter/render/html", _RENDER, [(gravis, "d3", _slow_figure)]),
])
def test_slow_work_does_not_hold_up_a_cheap_route(monkeypatch, slow_path, body, patches):
    for target, name, stand_in in patches:
        monkeypatch.setattr(target, name, stand_in)
    _waiting.clear()
    took, status = asyncio.run(_cheap_while(slow_path, body))
    assert status == 200
    assert took < CHEAP_WITHIN, (
        f"/parse/languages took {took:.2f}s while {slow_path} worked for {SLOW}s: "
        f"{slow_path} is blocking the event loop")
