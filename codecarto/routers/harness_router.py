"""What the harness is running and asking, for the Harness panel.

- `/harness/data` -- the tool runs, the questions held for a person and the
  instructions, each cut to the rows a panel shows with the number held back,
  and a run state for each project those rows name.

It answers in `generate_return`'s envelope with status 200. A harness that is
not answering is a `results` carrying `unreachable`, a `problem`, a `remedy`
and a `where`, as every estate route reports an absent seam.

The route reads. Nothing here posts to the harness.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from codecarto.services import harness_service
from codecarto.util.utilities import generate_return

HarnessRouter = APIRouter()


@HarnessRouter.get("/data")
async def harness_data() -> dict[str, Any]:
    """The harness's runs, queue and instructions, and the states they give.

    Read in the threadpool: the client blocks on HTTP for up to its timeout on
    each of three reads, and the event loop keeps serving meanwhile.
    """
    return generate_return(results=await run_in_threadpool(harness_service.read))
