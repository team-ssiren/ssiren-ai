"""경량 메트릭 — LLM 호출 수·토큰·지연·오류 누적 카운터.

프로세스 메모리 기반(스크레이프/재시작 시 초기화). GET /metrics 로 노출.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

_lock = threading.Lock()


@dataclass
class _Counters:
    llm_calls: int = 0
    llm_errors: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_latency_ms: float = 0.0


_counters = _Counters()


def record_llm(
    *, prompt_tokens: int, completion_tokens: int, latency_ms: float, error: bool = False
) -> None:
    with _lock:
        _counters.llm_calls += 1
        if error:
            _counters.llm_errors += 1
        _counters.prompt_tokens += prompt_tokens
        _counters.completion_tokens += completion_tokens
        _counters.total_latency_ms += latency_ms


def snapshot() -> dict:
    with _lock:
        c = _counters
        calls = c.llm_calls or 1
        return {
            "llm_calls": c.llm_calls,
            "llm_errors": c.llm_errors,
            "prompt_tokens": c.prompt_tokens,
            "completion_tokens": c.completion_tokens,
            "total_tokens": c.prompt_tokens + c.completion_tokens,
            "avg_latency_ms": round(c.total_latency_ms / calls, 1),
        }


def reset() -> None:
    global _counters
    with _lock:
        _counters = _Counters()
