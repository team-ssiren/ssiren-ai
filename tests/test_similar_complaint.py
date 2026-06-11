"""Public complaint similar-case lookup and normalization."""

import pytest

from app.schemas.public_complaint import PublicComplaintApiItem, PublicComplaintApiResponse
from app.services import public_complaint_client, similar_complaint


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_public_complaint_response_extracts_nested_items():
    payload = {
        "response": {
            "body": {
                "items": [
                    {
                        "title": " 도로 파손 문의 ",
                        "content": " 포트홀 보수 요청 ",
                        "create_date": "20260430145625",
                        "main_sub_name": "교통",
                        "dep_name": "도로관리과",
                    }
                ]
            }
        }
    }

    response = PublicComplaintApiResponse.from_payload(payload)

    assert len(response.items) == 1
    assert response.items[0].title == " 도로 파손 문의 "


@pytest.mark.anyio
async def test_search_similar_cases_normalizes_and_filters(monkeypatch):
    async def fake_fetch(_user_text):
        return [
            PublicComplaintApiItem(
                title=" 도로 파손 문의 ",
                content=" 포트홀 보수 요청 ",
                create_date="20260430145625",
                main_sub_name=" 교통 ",
                dep_name=" 도로관리과 ",
            ),
            PublicComplaintApiItem(title="  ", content="", dep_name="민원실"),
            PublicComplaintApiItem(title="", content="내용만 있는 사례", create_date="bad-date"),
        ]

    monkeypatch.setattr(public_complaint_client, "fetch_similar_complaints", fake_fetch)

    cases = await similar_complaint.search_similar_cases("도로가 파였어요")

    assert len(cases) == 2
    assert cases[0].title == "도로 파손 문의"
    assert cases[0].content == "포트홀 보수 요청"
    assert cases[0].createDate.year == 2026
    assert cases[0].mainSubName == "교통"
    assert cases[0].departmentName == "도로관리과"
    assert cases[0].embeddingText == "도로 파손 문의\n포트홀 보수 요청"
    assert cases[1].embeddingText == "내용만 있는 사례"
    assert cases[1].createDate is None


@pytest.mark.anyio
async def test_search_similar_cases_returns_empty_on_client_failure(monkeypatch):
    async def fake_fetch(_user_text):
        raise RuntimeError("boom")

    monkeypatch.setattr(public_complaint_client, "fetch_similar_complaints", fake_fetch)

    assert await similar_complaint.search_similar_cases("도로") == []
