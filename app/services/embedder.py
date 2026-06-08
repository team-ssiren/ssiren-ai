"""OpenAI 임베딩 서비스 (text-embedding-3-small).

임베딩을 OpenAI API 로 생성한다(로컬 GPU 연산 없음). OpenAI 임베딩은 unit-norm 이라
BE 는 내적(dot product)을 코사인 유사도로 그대로 사용할 수 있다.

⚠️ 임베딩 대상 텍스트 결합 규칙(`build_embedding_text`)은 ①(analyze)·②(embeddings)가
동일하게 사용해야 벡터 공간이 일치한다.
"""

from __future__ import annotations

from openai import OpenAIError

from app.config import get_settings
from app.core.errors import EmbeddingError
from app.core.llm import get_openai_client


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


async def embed(texts: list[str]) -> list[list[float]]:
    """OpenAI 임베딩 벡터 목록 반환(입력 순서 보존)."""
    if not texts:
        return []

    settings = get_settings()
    client = get_openai_client()
    try:
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
            dimensions=settings.embedding_dimension,
        )
    except OpenAIError as exc:
        raise EmbeddingError(f"embedding failed: {exc}") from exc

    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]
