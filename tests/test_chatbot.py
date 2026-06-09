"""Phase 3: chatbot plan/answer service + routes (mocked LLM)."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import chatbot as route
from app.main import app
from app.prompts.chatbot import build_answer_messages, build_plan_messages, build_title_messages
from app.schemas.chatbot import (
    ChatAnswerRequest,
    ChatAnswerResult,
    ChatContext,
    ChatMessage,
    ChatPlanResult,
    ChatTitleRequest,
    ChatTitleResult,
    ContextReport,
)
from app.services import chatbot

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- service: plan ------------------------------------------------------------
@pytest.mark.anyio
async def test_plan_search_nearby(monkeypatch):
    result = ChatPlanResult.model_validate(
        {
            "action": "SEARCH_NEARBY",
            "params": {"categoryCode": None, "radiusMeters": 500},
            "answer": None,
        }
    )

    async def fake_cs(*, messages, schema, **kw):
        assert schema is ChatPlanResult
        return result

    monkeypatch.setattr(chatbot, "complete_structured", fake_cs)
    from app.schemas.chatbot import ChatPlanRequest

    out = await chatbot.plan(ChatPlanRequest(question="이 근처 위험한 거 있어?"))
    assert out.action.value == "SEARCH_NEARBY"
    assert out.params.radiusMeters == 500


# --- service: answer grounding ------------------------------------------------
@pytest.mark.anyio
async def test_answer_grounded(monkeypatch):
    result = ChatAnswerResult(answer="약 120m 거리에 도로 파손 이슈가 있어요.", usedReportIds=[15])

    async def fake_cs(*, messages, schema, **kw):
        assert schema is ChatAnswerResult
        # context block present in system messages
        assert any("reportId=15" in m["content"] for m in messages if m["role"] == "system")
        return result

    monkeypatch.setattr(chatbot, "complete_structured", fake_cs)

    req = ChatAnswerRequest(
        question="이 근처 위험한 제보 있어?",
        context=ChatContext(
            scope="SEARCH_NEARBY",
            reports=[
                ContextReport(
                    reportId=15,
                    title="궁동 도로 파손",
                    summary="통행 위험",
                    category="도로 파손",
                    distanceMeters=120.0,
                    riskScore=66.0,
                )
            ],
        ),
    )
    out = await chatbot.answer(req)
    assert out.usedReportIds == [15]


# --- prompt: history window ---------------------------------------------------
def test_plan_history_window_limits():
    history = [ChatMessage(role="user", content=f"m{i}") for i in range(30)]
    msgs = build_plan_messages(question="q", history=history, limit=10)
    # 1 system + 10 history + 1 current user
    assert len(msgs) == 12
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["content"].endswith("q")


def test_answer_empty_context_renders_placeholder():
    msgs = build_answer_messages(
        question="근처 제보?",
        history=[],
        context=ChatContext(scope="SEARCH_NEARBY", reports=[]),
        limit=10,
    )
    assert any("제보 목록 없음" in m["content"] for m in msgs)


# --- routes -------------------------------------------------------------------
def test_plan_route(monkeypatch):
    async def fake_plan(req):
        return ChatPlanResult.model_validate(
            {
                "action": "ANSWER_DIRECT",
                "params": {"categoryCode": None, "radiusMeters": None},
                "answer": "안녕하세요!",
            }
        )

    monkeypatch.setattr(route.chatbot, "plan", fake_plan)
    resp = client.post("/internal/v1/chatbot:plan", json={"question": "안녕"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "ANSWER_DIRECT"
    assert body["answer"] == "안녕하세요!"


def test_answer_route(monkeypatch):
    async def fake_answer(req):
        return ChatAnswerResult(answer="주변에 접수된 제보가 없어요.", usedReportIds=[])

    monkeypatch.setattr(route.chatbot, "answer", fake_answer)
    resp = client.post(
        "/internal/v1/chatbot:answer",
        json={"question": "근처 제보?", "context": {"scope": "SEARCH_NEARBY", "reports": []}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["usedReportIds"] == []


# --- title --------------------------------------------------------------------
@pytest.mark.anyio
async def test_title_service(monkeypatch):
    async def fake_cs(*, messages, schema, **kw):
        assert schema is ChatTitleResult
        # first message present in the user turn
        assert any("이 근처 위험" in m["content"] for m in messages if m["role"] == "user")
        return ChatTitleResult(title="근처 위험 제보 문의")

    monkeypatch.setattr(chatbot, "complete_structured", fake_cs)
    out = await chatbot.title(ChatTitleRequest(question="이 근처 위험한 제보 있어?"))
    assert out.title == "근처 위험 제보 문의"


def test_build_title_messages_includes_optional_answer():
    with_answer = build_title_messages("이 근처 위험한 제보 있어?", "네, 도로 파손 이슈가 있어요.")
    user = with_answer[-1]["content"]
    assert "첫 메시지" in user
    assert "첫 응답" in user

    without = build_title_messages("안녕", None)
    assert "첫 응답" not in without[-1]["content"]


def test_title_route(monkeypatch):
    async def fake_title(req):
        return ChatTitleResult(title="도로 파손 문의")

    monkeypatch.setattr(route.chatbot, "title", fake_title)
    resp = client.post("/internal/v1/chatbot:title", json={"question": "도로가 파였어요"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "도로 파손 문의"
