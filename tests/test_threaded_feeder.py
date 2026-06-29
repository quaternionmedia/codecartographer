"""
Tests for codecarto.util.threaded_feeder.start_threaded_feeder — the
shared thread-spawn + queue-feed wiring extracted from
c_parser_router.py's /stream-github and pam_router.py's log tailer (see
docs/llm/next_steps/parser_consolidation_and_scope_drift.md, 2.2).
"""

import asyncio
import threading

import pytest

from codecarto.util.threaded_feeder import start_threaded_feeder


class TestStartThreadedFeeder:
    @pytest.mark.asyncio
    async def test_worker_runs_in_a_separate_thread(self):
        seen_thread_id = {}

        def make_worker(queue, loop):
            def worker():
                seen_thread_id["id"] = threading.get_ident()
                asyncio.run_coroutine_threadsafe(queue.put("done"), loop)
            return worker

        queue = start_threaded_feeder(make_worker)
        await queue.get()

        assert seen_thread_id["id"] != threading.get_ident()

    @pytest.mark.asyncio
    async def test_thread_is_daemon(self):
        def make_worker(queue, loop):
            def worker():
                asyncio.run_coroutine_threadsafe(
                    queue.put(threading.current_thread().daemon), loop
                )
            return worker

        queue = start_threaded_feeder(make_worker)
        is_daemon = await queue.get()

        assert is_daemon is True

    @pytest.mark.asyncio
    async def test_events_pushed_from_thread_are_received_in_order(self):
        def make_worker(queue, loop):
            def worker():
                for i in range(5):
                    asyncio.run_coroutine_threadsafe(queue.put(i), loop)
            return worker

        queue = start_threaded_feeder(make_worker)

        received = [await queue.get() for _ in range(5)]
        assert received == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_worker_factory_receives_a_real_queue_and_loop(self):
        captured = {}

        def make_worker(queue, loop):
            captured["queue"] = queue
            captured["loop"] = loop
            def worker():
                pass
            return worker

        returned_queue = start_threaded_feeder(make_worker)

        assert captured["queue"] is returned_queue
        assert isinstance(captured["queue"], asyncio.Queue)
        assert captured["loop"] is asyncio.get_running_loop()

    @pytest.mark.asyncio
    async def test_exception_in_worker_does_not_propagate_to_caller(self):
        """A worker that raises must not crash the calling coroutine — it's
        running in a separate OS thread, exceptions there are the worker's
        own responsibility to report (e.g. via queue.put({'__error__': ...}))."""
        def make_worker(queue, loop):
            def worker():
                try:
                    raise RuntimeError("boom")
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put("survived"), loop)
            return worker

        queue = start_threaded_feeder(make_worker)
        result = await queue.get()
        assert result == "survived"
