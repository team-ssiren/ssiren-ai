"""동시성 제한 — LLM·임베딩 호출에 상한을 둬 과부하/레이트리밋/GPU 경합을 방지.

세마포어는 앱 기동(lifespan, running loop 내부)에서 생성한다. 초기화 전에는
slot 이 no-op 이므로 lifespan 없이 도는 단위 테스트에는 영향이 없다.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

_llm_sem: asyncio.Semaphore | None = None
_embedding_sem: asyncio.Semaphore | None = None


def init_semaphores(llm_size: int, embedding_size: int) -> None:
    """Create semaphores bound to the current running loop (call from lifespan)."""
    global _llm_sem, _embedding_sem
    _llm_sem = asyncio.Semaphore(llm_size)
    _embedding_sem = asyncio.Semaphore(embedding_size)


def reset_semaphores() -> None:
    """Drop semaphores (used by tests to avoid cross-loop leakage)."""
    global _llm_sem, _embedding_sem
    _llm_sem = None
    _embedding_sem = None


@asynccontextmanager
async def llm_slot() -> AsyncIterator[None]:
    sem = _llm_sem
    if sem is None:
        yield
        return
    async with sem:
        yield


@asynccontextmanager
async def embedding_slot() -> AsyncIterator[None]:
    sem = _embedding_sem
    if sem is None:
        yield
        return
    async with sem:
        yield
