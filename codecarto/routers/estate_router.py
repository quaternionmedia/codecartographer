"""The estate's seams, and whether each is there: the liveness table.

**THIS ANSWERS "WHAT IS UP" WITHOUT DRAWING ANYTHING.** The three estate routers
each say, in their own envelope, when the thing behind them is missing. Nothing
said it *across* them -- a reader opening this window on a fresh workstation had
to open each panel to learn that nothing was running. `/estate/seams` is that
answer in one document: every seam this window reads, identified or not, with
the sentence that would change it.

**IDENTITY, NOT A PORT CHECK.** Each row comes from `estate_service`'s probes,
which ask the far side for a document whose shape this window knows. `ok` is
"answered with the shape expected", and *something answered and it was not the
harness* is reported as its own problem rather than as green.

**STATUS 200, ALWAYS, AND THE ABSENCES IN THE ROWS.** This route worked; the
things behind it may not have. It follows `topology_router._unreachable`'s rule
for the same mechanical reason -- the front end's request handler treats a
non-200 envelope as a fault in this service -- and for the honest one: an estate
with nothing up is not an error in the window looking at it.

WHAT THIS CANNOT DO. Start anything, or say a seam's content is current. It
reports presence and identity; each seam's own metadata carries its caveat.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from codecarto.services import estate_service
from codecarto.util.utilities import generate_return

EstateRouter = APIRouter()

#: The survey running now, which every request that arrives meanwhile awaits.
_survey: asyncio.Future | None = None


async def _shared_survey() -> list[dict[str, Any]]:
    """The running survey's rows, starting one only when none is running.

    **ONE SURVEY AT A TIME, AND ITS WAITERS ON THE LOOP.** A survey waits on
    other servers for four to twelve seconds when nothing is up, in a threadpool
    slot. One per request, a page that keeps asking fills the pool, and every
    other `run_in_threadpool` call in the server queues behind them. Requests
    that arrive while one runs await it here, holding no slot.

    **A FINISHED SURVEY IS NOT REUSED.** The next request probes afresh, so a
    seam brought up shows at once; a joiner's rows are at most one survey old.
    The task is shielded, so a client that goes away cancels its own wait and
    not the survey the others are waiting for.
    """
    global _survey
    running = _survey
    if running is None or running.done():
        running = asyncio.ensure_future(run_in_threadpool(estate_service.survey))
        _survey = running
    return await asyncio.shield(running)


@EstateRouter.get("/seams")
async def estate_seams() -> dict[str, Any]:
    """Every seam, probed once, with the caveat a reader needs first.

    The probes wait on other servers, up to their timeouts, so they run in the
    threadpool: on the event loop that wait would hold up every other request.
    `_shared_survey` says why concurrent requests share one.
    """
    rows = await _shared_survey()
    return generate_return(results={
        "seams": rows,
        "live": sum(1 for r in rows if r["ok"]),
        "caveat": estate_service.caveat(rows),
    })
