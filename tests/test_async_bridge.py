"""Tests for the sync-generator -> async-stream bridge."""

import asyncio

from src.core.async_bridge import stream_sync_generator


def _collect(make_gen):
    async def _run():
        out = []
        async for item in stream_sync_generator(make_gen):
            out.append(item)
        return out

    return asyncio.run(_run())


def test_streams_all_items_in_order():
    def gen():
        for i in range(5):
            yield f"tok{i}"

    assert _collect(gen) == ["tok0", "tok1", "tok2", "tok3", "tok4"]


def test_empty_generator_yields_nothing():
    def gen():
        return iter(())

    assert _collect(gen) == []


def test_generator_exception_is_reraised_after_prior_items():
    def gen():
        yield "a"
        yield "b"
        raise RuntimeError("boom")

    async def _run():
        seen = []
        try:
            async for item in stream_sync_generator(gen):
                seen.append(item)
        except RuntimeError as exc:
            return seen, str(exc)
        return seen, None

    seen, err = asyncio.run(_run())
    assert seen == ["a", "b"]
    assert err == "boom"
