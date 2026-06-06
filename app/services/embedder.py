"""bge-m3 임베딩 서비스 (sentence-transformers, GPU).

모델은 프로세스당 1회 로드(싱글톤). `embed()` 는 L2 정규화된 1024차원 dense 벡터를
반환하므로 BE 는 내적(dot product)을 코사인 유사도로 사용할 수 있다.

⚠️ 임베딩 대상 텍스트 결합 규칙(`build_embedding_text`)은 ①(analyze)·②(embeddings)가
동일하게 사용해야 벡터 공간이 일치한다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import get_settings
from app.core.errors import EmbeddingError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@lru_cache
def get_model() -> SentenceTransformer:
    """Lazy singleton bge-m3 model (cached for the process lifetime)."""
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.embedding_model, device=settings.embedding_device)


def warmup() -> None:
    """Force model load (called at startup so first request isn't cold)."""
    get_model()


def build_embedding_text(
    title: str | None = None,
    summary: str | None = None,
    keywords: list[str] | None = None,
) -> str:
    """제보의 임베딩 입력 텍스트 결합 규칙 — ①/② 공통."""
    parts = [
        (title or "").strip(),
        (summary or "").strip(),
        " ".join(keywords or []).strip(),
    ]
    return "\n".join(p for p in parts if p)


def embed(texts: list[str]) -> list[list[float]]:
    """L2 정규화된 임베딩 벡터 목록 반환."""
    if not texts:
        return []

    model = get_model()
    settings = get_settings()
    try:
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    except Exception as exc:  # noqa: BLE001 — surface as domain error
        raise EmbeddingError(f"embedding failed: {exc}") from exc

    result = vectors.tolist()
    expected = settings.embedding_dimension
    if result and len(result[0]) != expected:
        raise EmbeddingError(
            f"unexpected embedding dimension: got {len(result[0])}, expected {expected}"
        )
    return result
