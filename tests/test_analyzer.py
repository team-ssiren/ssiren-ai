"""다단계 analyzer 파이프라인 (LLM/DB/embedder 모킹)."""

import io
from datetime import datetime

import pytest
from PIL import Image

from app.db.repository import DepartmentRow, OrgRow
from app.schemas.pipeline import MajorResult
from app.schemas.public_complaint import RankedSimilarComplaintCase
from app.services import analyzer


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _img_bytes(w: int = 20, h: int = 20) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 120, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def _enrich_payload(risk=62.5, fscore=8.0, dept="건설과"):
    return {
        "title": "판교 도로 파손 제보",
        "contents": {
            "who": "확인되지 않음", "when": "2026-06-05T15:30:00", "where": "분당구",
            "what": "도로 파손", "how": "노면 파손", "why": "사고 위험",
            "summary": "판교 도로 파손으로 통행 안전 확인 필요.",
        },
        "keywords": ["도로 파손", "포트홀"],
        "riskScore": risk,
        "analysis": {
            "detectedObjects": ["도로"],
            "falseReport": {"isSuspicious": False, "score": fscore, "reason": "연관성 높음"},
            "emergencyGuide": {"isEmergency": False, "message": None},
        },
        "suggestedDepartment": dept,
        "assignmentReason": "도로 시설 보수는 건설과의 소관 사무이다.",
    }


def _install_stubs(
    monkeypatch,
    *,
    insufficient=False,
    risk=62.5,
    fscore=8.0,
    minor_conf=0.9,
    similar=None,
    embed=None,
):
    calls = []

    async def fake_cs(*, messages, schema, model=None, **kw):
        calls.append({"schema": schema, "messages": messages, "model": model})
        if schema is MajorResult:
            return MajorResult(
                majorCode="INFRASTRUCTURE_ROAD", confidence=0.95, insufficient=insufficient
            )
        if schema.__name__.startswith("MinorResult"):
            return schema(minorCode="ROAD_DAMAGE", confidence=minor_conf)
        return schema(**_enrich_payload(risk=risk, fscore=fscore))

    async def fake_find_top(_content):
        return similar or []

    async def fake_embed(texts):
        if embed is not None:
            embed["text"] = texts[0]
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(analyzer, "complete_structured", fake_cs)
    monkeypatch.setattr(analyzer.similar_complaint, "find_top_similar_cases", fake_find_top)
    monkeypatch.setattr(analyzer.embedder, "embed", fake_embed)
    monkeypatch.setattr(
        analyzer.repository, "get_assignment_guide", lambda mj, mn: "가이드 평문"
    )
    monkeypatch.setattr(
        analyzer.repository,
        "list_departments",
        lambda types, region: [DepartmentRow("지자체", "분당구청", "건설과", "031 729 7381")],
    )
    monkeypatch.setattr(
        analyzer.repository,
        "resolve_org",
        lambda region, dept: OrgRow("분당구청", "건설과", "031 729 7381", "지자체"),
    )
    return calls


@pytest.mark.anyio
async def test_three_step_assembly(monkeypatch):
    calls = _install_stubs(monkeypatch)
    resp = await analyzer.analyze(
        analyzer.AnalyzeInput(
            content="도로가 파였어요",
            latitude=37.39,
            longitude=127.11,
            images=[analyzer.ImageInput(data=_img_bytes())],
        )
    )
    assert [c["schema"].__name__ for c in calls][:1] == ["MajorResult"]
    assert len(calls) == 3  # major, minor, enrich
    assert resp.category.majorCode.value == "INFRASTRUCTURE_ROAD"
    assert resp.category.categoryCode.value == "ROAD_DAMAGE"
    assert resp.resolvedAgency.department == "건설과"
    assert resp.resolvedAgency.agencyType == "지자체"
    assert resp.resolvedAgency.name == "분당구청"
    assert resp.resolvedAgency.phone == "031 729 7381"
    assert resp.resolvedAgency.resolved is True
    assert len(resp.embedding) == 1536
    # 멀티모달: enrich(user) 메시지에 이미지 파트 주입
    enrich_user = calls[2]["messages"][1]["content"]
    assert any(p["type"] == "image_url" for p in enrich_user)


@pytest.mark.anyio
async def test_classify_steps_use_classify_model(monkeypatch):
    calls = _install_stubs(monkeypatch)
    await analyzer.analyze(analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0))
    cm = analyzer.get_settings().classify_model
    assert calls[0]["model"] == cm  # major
    assert calls[1]["model"] == cm  # minor
    assert calls[2]["model"] is None  # enrich → default (openai_model)


@pytest.mark.anyio
async def test_insufficient_short_circuits(monkeypatch):
    calls = _install_stubs(monkeypatch, insufficient=True)
    resp = await analyzer.analyze(
        analyzer.AnalyzeInput(content="ㅁㄴㅇㄹ", latitude=0.0, longitude=0.0)
    )
    assert len(calls) == 1  # only the major call ran
    assert resp.category.categoryCode.value == "INSUFFICIENT"
    assert resp.resolvedAgency.name is None
    assert resp.resolvedAgency.resolved is False
    assert resp.embedding == []


@pytest.mark.anyio
async def test_step2_insufficient_short_circuits(monkeypatch):
    # 1차 통과(ETC) 후 2차가 INSUFFICIENT 를 내도 방어 가드로 단락 — 보강/해소 스킵.
    from types import SimpleNamespace

    seen = []

    async def fake_cs(*, messages, schema, model=None, **kw):
        seen.append(schema.__name__)
        if schema is MajorResult:
            return MajorResult(majorCode="ETC", confidence=0.6, insufficient=False)
        if schema.__name__.startswith("MinorResult"):
            return SimpleNamespace(minorCode="INSUFFICIENT", confidence=0.4)
        raise AssertionError("enrich(3차) 가 호출되면 안 됨")

    async def fake_empty(_c):
        return []

    monkeypatch.setattr(analyzer, "complete_structured", fake_cs)
    monkeypatch.setattr(analyzer.similar_complaint, "find_top_similar_cases", fake_empty)

    resp = await analyzer.analyze(analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0))
    assert resp.category.categoryCode.value == "INSUFFICIENT"
    assert resp.resolvedAgency.resolved is False
    assert resp.embedding == []
    assert "EnrichResult" not in seen  # 보강 단계 진입 안 함


@pytest.mark.anyio
async def test_similar_complaints_injected_into_enrich(monkeypatch):
    similar = [
        RankedSimilarComplaintCase(
            title="포트홀 보수 요청",
            content="도로에 포트홀이 있어 보수 요청합니다.",
            createDate=datetime(2026, 4, 30),
            mainSubName="성남시 분당구",
            departmentName="건설과",
            embeddingScore=0.87,
        )
    ]
    calls = _install_stubs(monkeypatch, similar=similar)
    await analyzer.analyze(
        analyzer.AnalyzeInput(content="도로가 파였어요", latitude=37.39, longitude=127.11)
    )
    enrich_text = calls[2]["messages"][1]["content"][0]["text"]
    assert "[공공데이터 유사 민원 사례 TOP5]" in enrich_text
    assert "포트홀 보수 요청" in enrich_text
    assert "[선택 가능한 부서 후보]" in enrich_text
    assert "건설과" in enrich_text


@pytest.mark.anyio
async def test_scores_clamped(monkeypatch):
    _install_stubs(monkeypatch, risk=150.0, fscore=120.0, minor_conf=1.5)
    resp = await analyzer.analyze(
        analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0)
    )
    assert resp.riskScore == 100.0
    assert resp.analysis.falseReport.score == 100.0
    assert resp.category.confidence == 1.0


@pytest.mark.anyio
async def test_embedding_text_uses_title_summary_keywords(monkeypatch):
    seen: dict = {}
    _install_stubs(monkeypatch, embed=seen)
    await analyzer.analyze(analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0))
    assert "판교 도로 파손 제보" in seen["text"]  # title
    assert "통행 안전 확인" in seen["text"]  # summary
    assert "포트홀" in seen["text"]  # keyword


@pytest.mark.anyio
async def test_occurred_at_echoed_or_defaulted(monkeypatch):
    _install_stubs(monkeypatch)
    provided = await analyzer.analyze(
        analyzer.AnalyzeInput(
            content="x", latitude=0.0, longitude=0.0, occurred_at="2026-06-05T15:30:00"
        )
    )
    assert provided.occurredAt == "2026-06-05T15:30:00"
    defaulted = await analyzer.analyze(
        analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0)
    )
    assert defaulted.occurredAt
