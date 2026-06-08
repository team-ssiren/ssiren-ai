"""② 임베딩 엔드포인트 — POST /internal/v1/embeddings.

OpenAI 임베딩 벡터 생성만 담당(백필/재계산용). 코사인 유사도·저장·임계값은 BE.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.core.concurrency import embedding_slot
from app.schemas.embedding import EmbeddingRequest, EmbeddingResponse
from app.services import embedder

router = APIRouter(prefix="/internal/v1", tags=["embeddings"])


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(req: EmbeddingRequest) -> EmbeddingResponse:
    settings = get_settings()

    if len(req.texts) > settings.embedding_max_batch:
        raise HTTPException(
            status_code=422,
            detail=f"too many texts: {len(req.texts)} > {settings.embedding_max_batch}",
        )

    async with embedding_slot():
        vectors = await embedder.embed(req.texts)

    return EmbeddingResponse(
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
        embeddings=vectors,
    )
