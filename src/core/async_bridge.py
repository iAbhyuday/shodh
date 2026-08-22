"""Bridge a blocking (sync) generator into an async token stream.

The agent loop (:func:`src.core.agent_loop.run_agent_turn`) is a synchronous
generator that makes blocking LLM calls. To stream it from an async FastAPI
endpoint without blocking the event loop, we run it in a worker thread and
hand items back through a thread-safe queue.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, AsyncIterator, Callable, Iterator

_SENTINEL = object()


async def stream_sync_generator(make_gen: Callable[[], Iterator[Any]]) -> AsyncIterator[Any]:
    """Yield items from a sync generator produced by ``make_gen`` without
    blocking the event loop.

    The generator runs in a daemon thread; items are delivered through an
    asyncio queue. An exception raised inside the generator is re-raised on the
    consuming side after the items produced so far.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def worker() -> None:
        try:
            for item in make_gen():
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except Exception as exc:  # surface generator failures to the consumer
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = await queue.get()
        if item is _SENTINEL:
            break
        if isinstance(item, BaseException):
            raise item
        yield item
