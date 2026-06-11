"""① 구조화 분석 파이프라인.

멀티모달(이미지+텍스트+주소) → OpenAI Structured Output → 구조화 JSON.
점수는 후처리로 범위 클램프하고, 임베딩을 합성해 AnalyzeResponse 로 반환한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.core.concurrency import embedding_slot
from app.core.image import to_data_url
from app.core.structured import complete_structured
from app.prompts.analyze import build_messages
from app.schemas.report import AnalysisLLMOutput, AnalyzeResponse
from app.services import embedder, similar_complaint

logger = logging.getLogger("ssairen.analyzer")


@dataclass
class ImageInput:
    data: bytes
    content_type: str = "image/jpeg"


@dataclass
class AnalyzeInput:
    content: str
    latitude: float
    longitude: float
    occurred_at: str | None = None
    road_address: str | None = None
    sido: str | None = None
    sigungu: str | None = None
    eupmyeondong: str | None = None
    images: list[ImageInput] = field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


async def analyze(inp: AnalyzeInput) -> AnalyzeResponse:
    settings = get_settings()
    occurred_at = inp.occurred_at or datetime.now().isoformat(timespec="seconds")

    # Downscale each image to the pixel budget (CPU-bound -> threadpool).
    image_data_urls = [
        await run_in_threadpool(
            to_data_url, img.data, img.content_type, settings.analyze_max_image_pixels
        )
        for img in inp.images
    ]
    similar_complaints = await _find_similar_complaints(inp.content)

    messages = build_messages(
        content=inp.content,
        occurred_at=occurred_at,
        latitude=inp.latitude,
        longitude=inp.longitude,
        road_address=inp.road_address,
        sido=inp.sido,
        sigungu=inp.sigungu,
        eupmyeondong=inp.eupmyeondong,
        image_data_urls=image_data_urls,
        similar_complaints=similar_complaints,
    )

    llm: AnalysisLLMOutput = await complete_structured(
        messages=messages, schema=AnalysisLLMOutput
    )

    # Post-process: clamp model-reported scores into valid ranges.
    llm.riskScore = _clamp(llm.riskScore, 0.0, 100.0)
    llm.category.confidence = _clamp(llm.category.confidence, 0.0, 1.0)
    llm.analysis.falseReport.score = _clamp(llm.analysis.falseReport.score, 0.0, 100.0)

    # Synthesize embedding from the same text rule used by ② (title+summary+keywords).
    text = embedder.build_embedding_text(
        title=llm.title, summary=llm.contents.summary, keywords=llm.keywords
    )
    async with embedding_slot():
        vectors = await embedder.embed([text])
    embedding = vectors[0] if vectors else []

    data = llm.model_dump()
    data["occurredAt"] = occurred_at  # echo the resolved value (single source vs contents.when)
    data["embedding"] = embedding
    return AnalyzeResponse.model_validate(data)


async def _find_similar_complaints(content: str):
    try:
        return await similar_complaint.find_top_similar_cases(content)
    except Exception as exc:
        logger.warning("Similar complaint RAG lookup failed: %s", exc.__class__.__name__)
        return []
