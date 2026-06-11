"""① 구조화 분석 파이프라인 (다단계).

1차(대분류) → 2차(소분류) → [가이드+유사사례 컨텍스트] → 3차(보강 아웃풋+기관/부서)
→ SQLite 조직표로 실제 기관·부서 해소 → 임베딩 합성 → AnalyzeResponse.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.core import taxonomy
from app.core.concurrency import embedding_slot
from app.core.image import to_data_url
from app.core.structured import complete_structured
from app.core.taxonomy import INSUFFICIENT, MajorCategory
from app.db import repository
from app.prompts.classify import build_major_messages, build_minor_messages
from app.prompts.common import build_location_block
from app.prompts.enrich import build_enrich_messages
from app.schemas.pipeline import (
    MajorResult,
    build_enrich_result_model,
    build_minor_result_model,
)
from app.schemas.report import (
    Analysis,
    AnalyzeResponse,
    CategoryResult,
    EmergencyGuide,
    FalseReport,
    FiveW1H,
    ResolvedAgency,
)
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
    region = settings.org_default_region_code

    image_data_urls = [
        await run_in_threadpool(
            to_data_url, img.data, img.content_type, settings.analyze_max_image_pixels
        )
        for img in inp.images
    ]
    location_block = build_location_block(
        latitude=inp.latitude,
        longitude=inp.longitude,
        road_address=inp.road_address,
        sido=inp.sido,
        sigungu=inp.sigungu,
        eupmyeondong=inp.eupmyeondong,
    )

    # 유사 사례 검색은 카테고리와 독립 → 1·2차 분류와 겹쳐 선행 실행.
    similar_task = asyncio.create_task(_find_similar_complaints(inp.content))

    try:
        # --- 1차: 대분류 ---
        major_res: MajorResult = await complete_structured(
            messages=build_major_messages(
                content=inp.content,
                occurred_at=occurred_at,
                location_block=location_block,
                image_data_urls=image_data_urls,
            ),
            schema=MajorResult,
            model=settings.classify_model,
        )

        if major_res.insufficient:
            similar_task.cancel()
            return _insufficient_response(occurred_at, _clamp(major_res.confidence, 0.0, 1.0))

        major: MajorCategory = major_res.majorCode

        # --- 2차: 소분류 (대분류로 제약) ---
        minor_model = build_minor_result_model(major)
        minor_res = await complete_structured(
            messages=build_minor_messages(
                major=major,
                content=inp.content,
                occurred_at=occurred_at,
                location_block=location_block,
                image_data_urls=image_data_urls,
            ),
            schema=minor_model,
            model=settings.classify_model,
        )
        minor_code: str = str(minor_res.minorCode)

        # --- 컨텍스트: 가이드 + 후보 부서 (DB) ---
        agency_types = [t.value for t in taxonomy.candidate_agency_types(major)]
        guide_text, candidates = await asyncio.gather(
            run_in_threadpool(repository.get_assignment_guide, major.value, minor_code),
            run_in_threadpool(repository.list_departments, agency_types, region),
        )
        similar = await similar_task
    except BaseException:
        similar_task.cancel()
        raise

    # --- 3차: 보강 아웃풋 + 기관/부서 ---
    enrich_model = build_enrich_result_model([c.department for c in candidates])
    enriched = await complete_structured(
        messages=build_enrich_messages(
            major=major,
            minor_code=minor_code,
            content=inp.content,
            occurred_at=occurred_at,
            location_block=location_block,
            image_data_urls=image_data_urls,
            guide_text=guide_text,
            similar_complaints=similar,
            candidates=candidates,
        ),
        schema=enrich_model,
    )

    risk_score = _clamp(float(enriched.riskScore), 0.0, 100.0)
    analysis: Analysis = enriched.analysis
    analysis.falseReport.score = _clamp(analysis.falseReport.score, 0.0, 100.0)
    suggested_department: str = str(enriched.suggestedDepartment)

    # --- 부서 → 실제 기관·부서 해소 (기관유형은 부서에서 도출) ---
    resolved = await _resolve_department(candidates, region, suggested_department)

    # --- 임베딩 합성 (마지막) ---
    text = embedder.build_embedding_text(
        title=enriched.title, summary=enriched.contents.summary, keywords=enriched.keywords
    )
    async with embedding_slot():
        vectors = await embedder.embed([text])
    embedding = vectors[0] if vectors else []

    return AnalyzeResponse(
        title=enriched.title,
        contents=enriched.contents,
        keywords=enriched.keywords,
        category=CategoryResult(
            majorCode=major,
            categoryCode=minor_code,
            confidence=_clamp(float(minor_res.confidence), 0.0, 1.0),
        ),
        riskScore=risk_score,
        analysis=analysis,
        assignmentReason=str(enriched.assignmentReason),
        occurredAt=occurred_at,
        embedding=embedding,
        resolvedAgency=resolved,
    )


async def _resolve_department(
    candidates: list[repository.DepartmentRow], region: str, department: str
) -> ResolvedAgency:
    """부서명 → 실제 기관·부서. 후보(in-memory) 우선, 실패 시 조직표 조회.

    department/agencyType 은 항상 채워지고(AI 결정), name/phone 은 해소 시 채운다.
    """
    for c in candidates:  # enum 제약된 후보에서 정확 매칭 — 추가 DB 조회 불필요
        if c.department == department:
            return ResolvedAgency(
                agencyType=c.agency_type, department=c.department,
                name=c.agency_name, phone=c.phone or c.agency_phone, resolved=True,
            )
    org = await run_in_threadpool(repository.resolve_org, region, department)
    if org is not None:
        return ResolvedAgency(
            agencyType=org.agency_type, department=org.department,
            name=org.name, phone=org.phone, resolved=True,
        )
    # 해소 실패 — AI 가 고른 부서명은 보존, 기관 정보만 null
    return ResolvedAgency(
        agencyType=None, department=department or None, name=None, phone=None, resolved=False
    )


def _insufficient_response(occurred_at: str, confidence: float) -> AnalyzeResponse:
    """1차에서 제보 불성립 단락 — 분류/해소 단계 스킵, 최소 응답."""
    unknown = "확인되지 않음"
    return AnalyzeResponse(
        title="제보 불성립",
        contents=FiveW1H(
            who=unknown, when=occurred_at, where=unknown, what=unknown, how=unknown,
            why=unknown, summary="내용·이미지가 불충분하여 제보로 성립하지 않습니다.",
        ),
        keywords=[],
        category=CategoryResult(
            majorCode=MajorCategory.ETC, categoryCode=INSUFFICIENT, confidence=confidence
        ),
        riskScore=0.0,
        analysis=Analysis(
            detectedObjects=[],
            falseReport=FalseReport(isSuspicious=False, score=0.0, reason="제보 불성립"),
            emergencyGuide=EmergencyGuide(isEmergency=False, message=None),
        ),
        assignmentReason="제보가 성립하지 않아 기관·부서를 배정하지 않았습니다.",
        occurredAt=occurred_at,
        embedding=[],
        resolvedAgency=ResolvedAgency(
            agencyType=None, department=None, name=None, phone=None, resolved=False
        ),
    )


async def _find_similar_complaints(content: str):
    try:
        return await similar_complaint.find_top_similar_cases(content)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Similar complaint RAG lookup failed: %s", exc.__class__.__name__)
        return []
