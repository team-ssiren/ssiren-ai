"""/internal/v1/embeddings route shape and validation (mocked embed)."""

from fastapi.testclient import TestClient

from app.api.routes import embeddings as route
from app.main import app

client = TestClient(app)


async def _fake_embed(texts):
    return [[0.1] * 1536 for _ in texts]


def test_embeddings_returns_contract_shape(monkeypatch):
    monkeypatch.setattr(route.embedder, "embed", _fake_embed)

    resp = client.post("/internal/v1/embeddings", json={"texts": ["a", "b"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == "text-embedding-3-small"
    assert body["dimension"] == 1536
    assert len(body["embeddings"]) == 2
    assert len(body["embeddings"][0]) == 1536


def test_empty_texts_rejected():
    resp = client.post("/internal/v1/embeddings", json={"texts": []})
    assert resp.status_code == 422


def test_oversize_batch_rejected(monkeypatch):
    monkeypatch.setattr(route.embedder, "embed", _fake_embed)
    resp = client.post("/internal/v1/embeddings", json={"texts": ["x"] * 200})
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" not in body
    assert body["error"]["code"] == "validation_error"
