"""Phase 4-1: concurrency-limit semaphores."""

import asyncio

import pytest

from app.core import concurrency


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset():
    concurrency.reset_semaphores()
    yield
    concurrency.reset_semaphores()


@pytest.mark.anyio
async def test_slot_is_noop_when_uninitialized():
    # Without init, the slot just yields (no limiting, no error).
    async with concurrency.llm_slot():
        pass
    async with concurrency.embedding_slot():
        pass


@pytest.mark.anyio
async def test_semaphore_caps_concurrency():
    concurrency.init_semaphores(llm_size=1, embedding_size=1)

    state = {"active": 0, "max": 0}
    release = asyncio.Event()

    async def worker():
        async with concurrency.llm_slot():
            state["active"] += 1
            state["max"] = max(state["max"], state["active"])
            await release.wait()
            state["active"] -= 1

    t1 = asyncio.create_task(worker())
    t2 = asyncio.create_task(worker())
    await asyncio.sleep(0.05)  # let both attempt to acquire

    assert state["max"] == 1  # only one holds the slot at a time
    release.set()
    await asyncio.gather(t1, t2)
