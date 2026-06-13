"""Phase 2-1: analysis schema matches the AI-BE contract and is strict-compatible."""

import pytest
from pydantic import ValidationError

from app.schemas.report import AnalysisLLMOutput, AnalyzeResponse

VALID_LLM = {
    "title": "둔산동 갤러리아 앞 인도 파손으로 인한 보행 안전 위험",
    "contents": {
        "who": "보행 중인 시민",
        "when": "2026-05-28T07:40:00",
        "where": "둔산동 갤러리아 앞 인도",
        "what": "인도 블록 파손으로 낙상 위험",
        "how": "우천 물고임+보도블록 파손",
        "why": "낙상·부상 가능성",
        "summary": "둔산동 갤러리아 앞 인도 파손으로 보행자 낙상 위험.",
    },
    "keywords": ["인도 파손", "보행 위험", "낙상 위험"],
    "category": {
        "majorCode": "INFRASTRUCTURE_ROAD",
        "categoryCode": "ROAD_DAMAGE",
        "confidence": 0.92,
    },
    "riskScore": 62.5,
    "analysis": {
        "detectedObjects": ["보도블록", "균열"],
        "falseReport": {"isSuspicious": False, "score": 8.2, "reason": "연관성 높음"},
        "emergencyGuide": {"isEmergency": False, "message": None},
    },
    "assignmentReason": "맨홀·보도 시설 보수는 건설도로과의 소관 사무이다.",
}

_RESOLVED = {
    "agencyType": "지자체",
    "department": "건설도로과",
    "name": "수지구청",
    "phone": "031 729 7381",
    "resolved": True,
}


def test_valid_llm_output_parses():
    out = AnalysisLLMOutput.model_validate(VALID_LLM)
    assert out.category.categoryCode.value == "ROAD_DAMAGE"
    assert out.analysis.emergencyGuide.message is None


def test_invalid_category_code_rejected():
    bad = {**VALID_LLM, "category": {"categoryCode": "NOPE", "confidence": 0.5}}
    with pytest.raises(ValidationError):
        AnalysisLLMOutput.model_validate(bad)


def test_response_adds_embedding_and_occurred_at():
    resp = AnalyzeResponse.model_validate(
        {
            **VALID_LLM,
            "occurredAt": "2026-05-28T07:40:00",
            "embedding": [0.1] * 1024,
            "resolvedAgency": _RESOLVED,
        }
    )
    assert len(resp.embedding) == 1024
    assert resp.occurredAt == "2026-05-28T07:40:00"
    assert resp.resolvedAgency.name == "수지구청"
    assert resp.resolvedAgency.resolved is True
    # contract field names present (camelCase)
    dumped = resp.model_dump()
    for key in ("title", "contents", "keywords", "category", "riskScore", "analysis",
                "assignmentReason", "occurredAt", "embedding", "resolvedAgency"):
        assert key in dumped


def test_llm_schema_has_no_defaults():
    # OpenAI strict structured outputs requires every field to be required.
    schema = AnalysisLLMOutput.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"].keys())


def test_schema_is_openai_strict_compatible():
    # Guards that the schema converts to OpenAI's strict JSON schema without error.
    pytest.importorskip("openai")
    from openai.lib._pydantic import to_strict_json_schema

    strict = to_strict_json_schema(AnalysisLLMOutput)
    assert strict["additionalProperties"] is False
