"""단계별 LLM I/O 스키마 — enum 제약 검증."""

import pytest
from pydantic import ValidationError

from app.core.taxonomy import MajorCategory
from app.schemas.pipeline import (
    MajorResult,
    build_enrich_result_model,
    build_minor_result_model,
)

_CONTENTS = {k: "-" for k in ("who", "when", "where", "what", "how", "why", "summary")}
_ANALYSIS = {
    "detectedObjects": [],
    "falseReport": {"isSuspicious": False, "score": 0.0, "reason": "-"},
    "emergencyGuide": {"isEmergency": False, "message": None},
}


def test_major_result_enum_and_flag():
    m = MajorResult(majorCode="LIFE_SAFETY", confidence=0.8, insufficient=False)
    assert m.majorCode is MajorCategory.LIFE_SAFETY
    with pytest.raises(ValidationError):
        MajorResult(majorCode="NOPE", confidence=0.8, insufficient=False)


def test_minor_model_constrained_to_major():
    model = build_minor_result_model(MajorCategory.INFRASTRUCTURE_ROAD)
    ok = model(minorCode="MANHOLE_DRAIN_DAMAGE", confidence=0.9)
    assert ok.minorCode == "MANHOLE_DRAIN_DAMAGE"
    # ETC_OTHER 탈출구 허용
    assert model(minorCode="ETC_OTHER", confidence=0.1).minorCode == "ETC_OTHER"
    # 다른 대분류의 소분류는 거부
    with pytest.raises(ValidationError):
        model(minorCode="ILLEGAL_PARKING", confidence=0.9)


def test_insufficient_excluded_from_minor_enum():
    # INSUFFICIENT 는 1차 전용 — 어떤 대분류의 2차 enum 에도 없어야 함(ETC 포함).
    for major in MajorCategory:
        model = build_minor_result_model(major)
        with pytest.raises(ValidationError):
            model(minorCode="INSUFFICIENT", confidence=0.5)
    # ETC 대분류는 ETC_OTHER 만 허용
    etc = build_minor_result_model(MajorCategory.ETC)
    assert etc(minorCode="ETC_OTHER", confidence=0.5).minorCode == "ETC_OTHER"


def test_enrich_model_constrains_department_to_candidates():
    model = build_enrich_result_model(["건설과", "환경자원과"])
    payload = {
        "title": "t",
        "contents": _CONTENTS,
        "keywords": ["k"],
        "riskScore": 50.0,
        "analysis": _ANALYSIS,
        "suggestedDepartment": "건설과",
        "assignmentReason": "건설과의 소관 사무이다.",
    }
    assert model(**payload).suggestedDepartment == "건설과"
    with pytest.raises(ValidationError):
        model(**{**payload, "suggestedDepartment": "없는과"})


def test_enrich_model_free_text_when_no_candidates():
    model = build_enrich_result_model([])
    payload = {
        "title": "t",
        "contents": _CONTENTS,
        "keywords": [],
        "riskScore": 0.0,
        "analysis": _ANALYSIS,
        "suggestedDepartment": "임의 부서명",
        "assignmentReason": "후보가 없어 자유 텍스트.",
    }
    assert model(**payload).suggestedDepartment == "임의 부서명"
