"""프롬프트 빌더 — 분류/보강 메시지 구성 검증."""

from datetime import datetime

from app.core.taxonomy import MajorCategory
from app.db.repository import DepartmentRow
from app.prompts.classify import build_major_messages, build_minor_messages
from app.prompts.common import build_location_block
from app.prompts.enrich import build_enrich_messages
from app.schemas.public_complaint import RankedSimilarComplaintCase

LOC = build_location_block(
    latitude=37.39,
    longitude=127.11,
    road_address="경기 성남시 분당구 판교역로 166",
    sido="경기도",
    sigungu="용인시 수지구",
    eupmyeondong="백현동",
)


def test_major_messages_list_all_majors_and_image():
    msgs = build_major_messages(
        content="맨홀이 깨졌어요",
        occurred_at="2026-06-11T23:50:00",
        location_block=LOC,
        image_data_urls=["data:image/jpeg;base64,AAA"],
    )
    assert msgs[0]["role"] == "system"
    for major in MajorCategory:
        assert major.value in msgs[0]["content"]
    parts = msgs[1]["content"]
    assert parts[0]["type"] == "text" and "판교역로 166" in parts[0]["text"]
    assert any(p["type"] == "image_url" for p in parts)


def test_minor_messages_scope_to_major():
    msgs = build_minor_messages(
        major=MajorCategory.INFRASTRUCTURE_ROAD,
        content="맨홀이 깨졌어요",
        occurred_at="2026-06-11T23:50:00",
        location_block=LOC,
        image_data_urls=[],
    )
    system = msgs[0]["content"]
    assert "MANHOLE_DRAIN_DAMAGE" in system
    assert "ILLEGAL_PARKING" not in system  # 다른 대분류 소분류 제외


def test_enrich_messages_inject_guide_candidates_similar():
    similar = [
        RankedSimilarComplaintCase(
            title="맨홀 보수",
            content="맨홀 뚜껑 파손",
            createDate=datetime(2026, 4, 30),
            mainSubName="용인시 수지구",
            departmentName="건설도로과",
            embeddingScore=0.91,
        )
    ]
    candidates = [DepartmentRow("지자체", "수지구청", "건설도로과", "031-1")]
    msgs = build_enrich_messages(
        major=MajorCategory.INFRASTRUCTURE_ROAD,
        minor_code="MANHOLE_DRAIN_DAMAGE",
        content="맨홀이 깨졌어요",
        occurred_at="2026-06-11T23:50:00",
        location_block=LOC,
        image_data_urls=["data:image/jpeg;base64,AAA"],
        guide_text="맨홀 배정 가이드 본문",
        similar_complaints=similar,
        candidates=candidates,
    )
    text = msgs[1]["content"][0]["text"]
    assert "[기관·부서 배정 근거자료]" in text and "맨홀 배정 가이드 본문" in text
    assert "[선택 가능한 부서 후보]" in text and "건설도로과" in text
    assert "[공공데이터 유사 민원 사례 TOP5]" in text and "맨홀 보수" in text
    assert "MANHOLE_DRAIN_DAMAGE" in text
    assert any(p["type"] == "image_url" for p in msgs[1]["content"])


def test_enrich_messages_omit_empty_blocks():
    msgs = build_enrich_messages(
        major=MajorCategory.TRAFFIC,
        minor_code="ILLEGAL_PARKING",
        content="불법주차",
        occurred_at="2026-06-11T23:50:00",
        location_block=LOC,
        image_data_urls=[],
        guide_text=None,
        similar_complaints=[],
        candidates=[],
    )
    text = msgs[1]["content"][0]["text"]
    assert "[기관·부서 배정 근거자료]" not in text
    assert "[선택 가능한 부서 후보]" not in text
    assert "[공공데이터 유사 민원 사례 TOP5]" not in text
