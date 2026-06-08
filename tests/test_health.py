"""Phase 0-1: /health smoke test."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "ssairen-ai"
    assert "version" in body
    assert body["models"]["embedding"] == "text-embedding-3-small"
    assert body["models"]["embedding_dimension"] == 1536
