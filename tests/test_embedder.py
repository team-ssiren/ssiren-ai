"""Embedder: text-combination rule and OpenAI embed() behavior (mocked client)."""

import pytest

from app.core.errors import EmbeddingError
from app.services import embedder


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_build_embedding_text_combines_fields():
    text = embedder.build_embedding_text(
        title="궁동 도로 파손",
        summary="통행 안전 확인 필요",
        keywords=["도로 파손", "포트홀"],
    )
    assert text == "궁동 도로 파손\n통행 안전 확인 필요\n도로 파손 포트홀"


def test_build_embedding_text_skips_empty():
    assert embedder.build_embedding_text(title="제목만", summary=None, keywords=[]) == "제목만"


def _fake_client(*, vectors=None, error=None):
    class _Item:
        def __init__(self, index, embedding):
            self.index = index
            self.embedding = embedding

    class _Resp:
        def __init__(self, data):
            self.data = data

    class _Embeddings:
        async def create(self, *, model, input, dimensions):
            if error is not None:
                raise error
            # return out-of-order to verify sorting by index
            data = [_Item(i, [float(i)] * dimensions) for i in range(len(input))]
            return _Resp(list(reversed(data)))

    class _Client:
        embeddings = _Embeddings()

    return _Client()


@pytest.mark.anyio
async def test_embed_empty_returns_empty():
    assert await embedder.embed([]) == []


@pytest.mark.anyio
async def test_embed_returns_vectors_in_input_order(monkeypatch):
    monkeypatch.setattr(embedder, "get_openai_client", lambda: _fake_client())

    vectors = await embedder.embed(["a", "b", "c"])
    assert len(vectors) == 3
    assert len(vectors[0]) == 1536
    # sorted by index -> first vector corresponds to input[0]
    assert vectors[0][0] == 0.0
    assert vectors[1][0] == 1.0
    assert vectors[2][0] == 2.0


@pytest.mark.anyio
async def test_embed_upstream_error_raises(monkeypatch):
    from openai import OpenAIError

    monkeypatch.setattr(
        embedder, "get_openai_client", lambda: _fake_client(error=OpenAIError("boom"))
    )
    with pytest.raises(EmbeddingError):
        await embedder.embed(["x"])
