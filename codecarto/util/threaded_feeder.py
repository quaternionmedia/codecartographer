"""
Threaded Feeder
================
Shared setup for the "background thread feeds an asyncio.Queue" pattern
used by SSE/WebSocket endpoints that wrap blocking or CPU-bound work
(libclang parsing, tailing a log file) without freezing the event loop.

Before this, c_parser_router.py's /stream-github and pam_router.py's log
tailer each hand-rolled the same thread-spawn + queue-feed wiring
independently — see docs/llm/next_steps/parser_consolidation_and_scope_drift.md,
finding 2.2. c_parser_router.py's own comment even named the duplication
("same pattern as pam_router.py's log tailer") without it ever being lifted.
"""

import asyncio
import threading
from typing import Callable


def start_threaded_feeder(
    worker_factory: Callable[[asyncio.Queue, asyncio.AbstractEventLoop], Callable[[], None]],
) -> asyncio.Queue:
    """Create an ``asyncio.Queue``, capture the running event loop, and
    start a daemon thread running the worker *worker_factory* builds.

    *worker_factory* receives the queue and loop and must return a
    zero-arg callable — the actual thread target — so it can close over
    them to call ``asyncio.run_coroutine_threadsafe(queue.put(...), loop)``
    from inside the thread. The two real call sites' worker shapes differ
    enough (one is a zero-arg closure with no other args; one tails a log
    file and takes a path) that only this setup step is unified, not the
    full worker body.

    This centralizes the part most likely to have a subtle bug: forgetting
    ``daemon=True`` (which would keep the process alive on shutdown), or
    capturing the loop from inside the thread instead of before starting
    it — ``asyncio.get_running_loop()`` only works from the event-loop
    thread; a plain OS thread has no running loop of its own and would
    raise ``RuntimeError``.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    threading.Thread(target=worker_factory(queue, loop), daemon=True).start()
    return queue
