"""Phase 4-1: metrics counters, /metrics endpoint, and graceful LLM failure."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import reports as reports_route
from app.core import metrics
from app.core.errors import LLMError
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_metrics():
    metrics.reset()
    yield
    metrics.reset()


def test_record_and_snapshot():
    metrics.record_llm(prompt_tokens=100, completion_tokens=20, latency_ms=300.0)
    metrics.record_llm(prompt_tokens=50, completion_tokens=10, latency_ms=100.0)
    snap = metrics.snapshot()
    assert snap["llm_calls"] == 2
    assert snap["total_tokens"] == 180
    assert snap["avg_latency_ms"] == 200.0
    assert snap["llm_errors"] == 0


def test_error_counted():
    metrics.record_llm(prompt_tokens=0, completion_tokens=0, latency_ms=10.0, error=True)
    assert metrics.snapshot()["llm_errors"] == 1


def test_metrics_endpoint():
    metrics.record_llm(prompt_tokens=10, completion_tokens=5, latency_ms=50.0)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.json()["llm_calls"] == 1


def test_llm_failure_returns_standard_error(monkeypatch):
    # Inject an upstream LLM failure on the analyze path; server must not crash,
    # and must respond with the standard error envelope (502).
    async def boom(inp):
        raise LLMError("upstream down")

    monkeypatch.setattr(reports_route.analyzer, "analyze", boom)
    resp = client.post(
        "/internal/v1/reports:analyze",
        data={"content": "도로 파손", "latitude": "36.3", "longitude": "127.3"},
    )
    assert resp.status_code == 502
    body = resp.json()
    assert body["error"]["code"] == "llm_upstream_error"
    assert body["error"]["requestId"]
