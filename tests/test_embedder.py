"""Phase 1-1: embedder text-combination rule and embed() behavior (mocked model)."""

import numpy as np

from app.services import embedder


def test_build_embedding_text_combines_fields():
    text = embedder.build_embedding_text(
        title="궁동 도로 파손",
        summary="통행 안전 확인 필요",
        keywords=["도로 파손", "포트홀"],
    )
    assert text == "궁동 도로 파손\n통행 안전 확인 필요\n도로 파손 포트홀"


def test_build_embedding_text_skips_empty():
    assert embedder.build_embedding_text(title="제목만", summary=None, keywords=[]) == "제목만"


def test_embed_empty_returns_empty():
    assert embedder.embed([]) == []


def test_embed_uses_model_and_returns_lists(monkeypatch):
    class _FakeModel:
        def encode(self, texts, normalize_embeddings, convert_to_numpy):
            assert normalize_embeddings is True
            # return 1024-dim unit-ish vectors
            return np.ones((len(texts), 1024), dtype=np.float32) / np.sqrt(1024)

    monkeypatch.setattr(embedder, "get_model", lambda: _FakeModel())

    vectors = embedder.embed(["a", "b"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    # L2 norm ~ 1
    assert abs(np.linalg.norm(vectors[0]) - 1.0) < 1e-4


def test_embed_wrong_dimension_raises(monkeypatch):
    import pytest

    from app.core.errors import EmbeddingError

    class _BadModel:
        def encode(self, texts, normalize_embeddings, convert_to_numpy):
            return np.ones((len(texts), 768), dtype=np.float32)

    monkeypatch.setattr(embedder, "get_model", lambda: _BadModel())
    with pytest.raises(EmbeddingError):
        embedder.embed(["x"])
