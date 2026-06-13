"""Phase 2-3: /internal/v1/reports:analyze multipart route + guards (mocked analyzer)."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import reports as route
from app.main import app
from app.schemas.report import AnalyzeResponse

client = TestClient(app)

_FAKE = AnalyzeResponse.model_validate(
    {
        "title": "궁동 도로 파손 제보",
        "contents": {
            "who": "확인되지 않음",
            "when": "2026-06-05T15:30:00",
            "where": "대전광역시 유성구 궁동",
            "what": "도로 파손",
            "how": "노면 파손",
            "why": "사고 위험",
            "summary": "궁동 도로 파손.",
        },
        "keywords": ["도로 파손"],
        "category": {
            "majorCode": "INFRASTRUCTURE_ROAD",
            "categoryCode": "ROAD_DAMAGE",
            "confidence": 0.9,
        },
        "riskScore": 62.5,
        "analysis": {
            "detectedObjects": ["도로"],
            "falseReport": {"isSuspicious": False, "score": 8.0, "reason": "ok"},
            "emergencyGuide": {"isEmergency": False, "message": None},
        },
        "assignmentReason": "도로 시설 보수는 건설도로과의 소관 사무이다.",
        "occurredAt": "2026-06-05T15:30:00",
        "embedding": [0.1] * 1024,
        "resolvedAgency": {
            "agencyType": "지자체",
            "department": "건설도로과",
            "name": "수지구청",
            "phone": "031 729 7381",
            "resolved": True,
        },
    }
)


@pytest.fixture(autouse=True)
def _mock_analyze(monkeypatch):
    async def fake_analyze(inp):
        fake_analyze.last = inp
        return _FAKE

    monkeypatch.setattr(route.analyzer, "analyze", fake_analyze)
    return fake_analyze


def _form():
    return {"content": "도로가 파였어요", "latitude": "36.3665", "longitude": "127.3447"}


def test_analyze_with_image(_mock_analyze):
    resp = client.post(
        "/internal/v1/reports:analyze",
        data=_form(),
        files=[("images", ("a.jpg", b"\xff\xd8\xff\xd9", "image/jpeg"))],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["category"]["categoryCode"] == "ROAD_DAMAGE"
    assert len(body["embedding"]) == 1024
    assert len(_mock_analyze.last.images) == 1


def test_analyze_text_only(_mock_analyze):
    resp = client.post("/internal/v1/reports:analyze", data=_form())
    assert resp.status_code == 200, resp.text
    assert _mock_analyze.last.images == []


def test_non_image_file_rejected():
    resp = client.post(
        "/internal/v1/reports:analyze",
        data=_form(),
        files=[("images", ("note.txt", b"hello", "text/plain"))],
    )
    assert resp.status_code == 422
    # guard error must use the standard envelope, not FastAPI's {"detail": ...}
    body = resp.json()
    assert "detail" not in body
    assert body["error"]["code"] == "validation_error"


def test_too_many_images_rejected():
    files = [("images", (f"{i}.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")) for i in range(6)]
    resp = client.post("/internal/v1/reports:analyze", data=_form(), files=files)
    assert resp.status_code == 422


def test_missing_required_field_rejected():
    resp = client.post(
        "/internal/v1/reports:analyze",
        data={"content": "x", "latitude": "36.3"},  # missing longitude
    )
    assert resp.status_code == 422
