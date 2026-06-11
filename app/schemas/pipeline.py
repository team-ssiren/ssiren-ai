"""단계별 LLM I/O 스키마.

1차(대분류)·2차(소분류)·3차(보강 아웃풋). 2·3차는 후보를 런타임에 enum 제약하기 위해
`Literal` 로 동적 모델을 생성한다(부서명이 숫자로 시작해 enum 멤버명으로 못 쓰는 경우 회피).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, create_model

from app.core import taxonomy
from app.core.taxonomy import MajorCategory
from app.schemas.report import Analysis, FiveW1H


class MajorResult(BaseModel):
    """1차: 대분류 + 제보 불성립 단락 신호."""

    majorCode: MajorCategory
    confidence: float
    insufficient: bool  # True 면 INSUFFICIENT 로 단락(2~5단계 스킵)


def build_minor_result_model(major: MajorCategory) -> type[BaseModel]:
    """2차: 해당 대분류의 소분류(+ETC_OTHER 탈출구)로 제약된 결과 모델."""
    codes = [leaf.code for leaf in taxonomy.minors_of(major)]
    if taxonomy.ETC_OTHER not in codes:
        codes.append(taxonomy.ETC_OTHER)
    minor_type = Literal[tuple(codes)]  # type: ignore[valid-type]
    return create_model(
        f"MinorResult_{major.value}",
        minorCode=(minor_type, ...),
        confidence=(float, ...),
    )


def build_enrich_result_model(candidate_departments: list[str]) -> type[BaseModel]:
    """3차: 보강 아웃풋 + 기관종류 + (후보 제약된) 부서종류."""
    if candidate_departments:
        unique = tuple(dict.fromkeys(candidate_departments))  # dedup, keep order
        dept_type: object = Literal[unique]
    else:
        dept_type = str  # 후보가 없으면 자유 텍스트(해소 단계에서 contains 매칭)
    return create_model(
        "EnrichResult",
        title=(str, ...),
        contents=(FiveW1H, ...),
        keywords=(list[str], ...),
        riskScore=(float, ...),
        analysis=(Analysis, ...),
        suggestedDepartment=(dept_type, ...),  # 후보 부서로 enum 제약(기관유형은 부서에서 도출)
        assignmentReason=(str, ...),  # 부서 배정 근거
    )
