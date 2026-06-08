"""Phase 2-2: analyzer pipeline (mocked LLM + embedder) and prompt assembly."""

import io

import pytest
from PIL import Image

from app.prompts.analyze import build_messages, get_system_prompt
from app.schemas.report import AnalysisLLMOutput
from app.services import analyzer


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _stub_embed(texts):
    return [[0.1] * 1536 for _ in texts]


def _img_bytes(w: int = 20, h: int = 20) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 120, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def _make_llm(risk=62.5, conf=0.9, fscore=8.0) -> AnalysisLLMOutput:
    return AnalysisLLMOutput.model_validate(
        {
            "title": "궁동 도로 파손 제보",
            "contents": {
                "who": "확인되지 않음",
                "when": "2026-06-05T15:30:00",
                "where": "대전광역시 유성구 궁동",
                "what": "도로 파손",
                "how": "노면 파손으로 통행 위험",
                "why": "사고 위험",
                "summary": "궁동 도로 파손으로 통행 안전 확인 필요.",
            },
            "keywords": ["도로 파손", "포트홀"],
            "category": {"categoryCode": "ROAD_DAMAGE", "confidence": conf},
            "riskScore": risk,
            "analysis": {
                "detectedObjects": ["도로", "균열"],
                "falseReport": {"isSuspicious": False, "score": fscore, "reason": "연관성 높음"},
                "emergencyGuide": {"isEmergency": False, "message": None},
            },
        }
    )


@pytest.mark.anyio
async def test_analyze_assembles_response_with_embedding(monkeypatch):
    captured = {}

    async def fake_cs(*, messages, schema, **kw):
        captured["messages"] = messages
        captured["schema"] = schema
        return _make_llm()

    monkeypatch.setattr(analyzer, "complete_structured", fake_cs)
    monkeypatch.setattr(analyzer.embedder, "embed", _stub_embed)

    resp = await analyzer.analyze(
        analyzer.AnalyzeInput(
            content="도로가 파였어요",
            latitude=36.3665,
            longitude=127.3447,
            images=[analyzer.ImageInput(data=_img_bytes(), content_type="image/jpeg")],
        )
    )

    assert resp.category.categoryCode.value == "ROAD_DAMAGE"
    assert len(resp.embedding) == 1536
    assert captured["schema"] is AnalysisLLMOutput
    # multimodal: image part injected into user message
    user_parts = captured["messages"][1]["content"]
    assert any(p["type"] == "image_url" for p in user_parts)


@pytest.mark.anyio
async def test_scores_are_clamped(monkeypatch):
    async def fake_cs(**kw):
        return _make_llm(risk=150.0, conf=1.5, fscore=120.0)

    monkeypatch.setattr(analyzer, "complete_structured", fake_cs)
    monkeypatch.setattr(analyzer.embedder, "embed", _stub_embed)

    resp = await analyzer.analyze(
        analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0)
    )
    assert resp.riskScore == 100.0
    assert resp.category.confidence == 1.0
    assert resp.analysis.falseReport.score == 100.0


@pytest.mark.anyio
async def test_embedding_text_uses_title_summary_keywords(monkeypatch):
    seen = {}

    async def fake_cs(**kw):
        return _make_llm()

    async def fake_embed(texts):
        seen["text"] = texts[0]
        return [[0.1] * 1536]

    monkeypatch.setattr(analyzer, "complete_structured", fake_cs)
    monkeypatch.setattr(analyzer.embedder, "embed", fake_embed)

    await analyzer.analyze(analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0))
    text = seen["text"]
    assert "궁동 도로 파손 제보" in text  # title
    assert "통행 안전 확인" in text  # summary
    assert "포트홀" in text  # keyword


@pytest.mark.anyio
async def test_occurred_at_echoed_or_defaulted(monkeypatch):
    async def fake_cs(**kw):
        return _make_llm()

    monkeypatch.setattr(analyzer, "complete_structured", fake_cs)
    monkeypatch.setattr(analyzer.embedder, "embed", _stub_embed)

    # provided -> echoed verbatim
    provided = await analyzer.analyze(
        analyzer.AnalyzeInput(
            content="x", latitude=0.0, longitude=0.0, occurred_at="2026-06-05T15:30:00"
        )
    )
    assert provided.occurredAt == "2026-06-05T15:30:00"

    # missing -> server default (non-empty), still returned so BE can reuse it
    defaulted = await analyzer.analyze(
        analyzer.AnalyzeInput(content="x", latitude=0.0, longitude=0.0)
    )
    assert defaulted.occurredAt


def test_build_messages_without_images():
    msgs = build_messages(
        content="쓰레기가 쌓여있어요",
        occurred_at="2026-06-05T15:30:00",
        latitude=36.3,
        longitude=127.3,
        road_address="대전광역시 유성구 대학로 99",
        image_data_urls=[],
    )
    assert msgs[0]["role"] == "system"
    user_parts = msgs[1]["content"]
    assert all(p["type"] == "text" for p in user_parts)
    assert "대학로 99" in user_parts[0]["text"]


def test_system_prompt_includes_taxonomy_and_rules():
    prompt = get_system_prompt()
    assert "ROAD_DAMAGE" in prompt
    assert "ETC_OTHER" in prompt
    assert "타이브레이크" in prompt
    assert "riskScore" in prompt
