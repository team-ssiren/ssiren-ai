"""Public complaint similar-case lookup and normalization."""

from datetime import datetime, timedelta

import pytest

from app.schemas.public_complaint import (
    PublicComplaintApiItem,
    PublicComplaintApiResponse,
    SimilarComplaintCase,
)
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


def test_cosine_similarity_handles_invalid_vectors():
    assert similar_complaint.cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert similar_complaint.cosine_similarity([], [1.0]) is None
    assert similar_complaint.cosine_similarity([1.0], [1.0, 0.0]) is None
    assert similar_complaint.cosine_similarity([0.0, 0.0], [1.0, 0.0]) is None


def test_rerank_score_components():
    now = datetime(2026, 6, 11)

    assert similar_complaint.calculate_department_score("성남소방서 119안전센터") == 10.0
    assert similar_complaint.calculate_department_score("일반민원실") == 0.0
    assert similar_complaint.calculate_recency_score(now - timedelta(days=100), now) == 10.0
    assert similar_complaint.calculate_recency_score(now - timedelta(days=800), now) == 7.0
    assert similar_complaint.calculate_recency_score(None, now) == 0.0
    assert similar_complaint.calculate_rerank_score(0.8, 10.0, 10.0) == 84.0


@pytest.mark.anyio
async def test_find_top_similar_cases_ranks_by_embedding_score(monkeypatch):
    async def fake_search(_user_text):
        return [
            _case("높은 유사도", "도로 파손"),
            _case("낮은 유사도", "소음 민원"),
            _case("중간 유사도", "보도 파손"),
        ]

    async def fake_embed(texts):
        assert texts == [
            "도로 파손 신고",
            "높은 유사도\n도로 파손",
            "낮은 유사도\n소음 민원",
            "중간 유사도\n보도 파손",
        ]
        return [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0],
            [0.8, 0.6],
        ]

    monkeypatch.setattr(similar_complaint, "search_similar_cases", fake_search)
    monkeypatch.setattr(similar_complaint.embedder, "embed", fake_embed)

    ranked_cases = await similar_complaint.find_top_similar_cases("도로 파손 신고")

    assert [case.title for case in ranked_cases] == ["높은 유사도", "중간 유사도"]
    assert ranked_cases[0].embeddingScore > ranked_cases[1].embeddingScore


@pytest.mark.anyio
async def test_find_top_similar_cases_reranks_with_department_bonus(monkeypatch):
    async def fake_search(_user_text):
        return [
            _case("임베딩만 높은 사례", "도로 파손", department_name="일반민원실"),
            _case("부서 가점 사례", "도로 보수", department_name="건설과"),
        ]

    async def fake_embed(_texts):
        return [
            [1.0, 0.0],
            [0.9, 0.435889],
            [0.8, 0.6],
        ]

    monkeypatch.setattr(similar_complaint, "search_similar_cases", fake_search)
    monkeypatch.setattr(similar_complaint.embedder, "embed", fake_embed)

    ranked_cases = await similar_complaint.find_top_similar_cases("도로 파손 신고")

    assert [case.title for case in ranked_cases] == ["부서 가점 사례", "임베딩만 높은 사례"]
    assert ranked_cases[0].departmentScore == 10.0
    assert ranked_cases[0].rerankScore > ranked_cases[1].rerankScore


@pytest.mark.anyio
async def test_find_top_similar_cases_returns_empty_on_embedding_failure(monkeypatch):
    async def fake_search(_user_text):
        return [_case("도로", "파손")]

    async def fake_embed(_texts):
        raise RuntimeError("boom")

    monkeypatch.setattr(similar_complaint, "search_similar_cases", fake_search)
    monkeypatch.setattr(similar_complaint.embedder, "embed", fake_embed)

    assert await similar_complaint.find_top_similar_cases("도로") == []


@pytest.mark.anyio
async def test_find_top_similar_cases_returns_empty_on_embedding_count_mismatch(monkeypatch):
    async def fake_search(_user_text):
        return [_case("도로", "파손")]

    async def fake_embed(_texts):
        return [[1.0, 0.0]]

    monkeypatch.setattr(similar_complaint, "search_similar_cases", fake_search)
    monkeypatch.setattr(similar_complaint.embedder, "embed", fake_embed)

    assert await similar_complaint.find_top_similar_cases("도로") == []


def _case(
    title: str,
    content: str,
    department_name: str | None = None,
) -> SimilarComplaintCase:
    return SimilarComplaintCase(
        title=title,
        content=content,
        createDate=None,
        mainSubName=None,
        departmentName=department_name,
        embeddingText=f"{title}\n{content}",
    )
