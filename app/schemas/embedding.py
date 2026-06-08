"""② 임베딩 엔드포인트 요청/응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="임베딩할 텍스트 목록")


class EmbeddingResponse(BaseModel):
    model: str
    dimension: int
    embeddings: list[list[float]]
