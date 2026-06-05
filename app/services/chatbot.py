"""③ 챗봇 서비스 — stateless 2-스텝.

plan: 질문+이력 → action 라우팅(ANSWER_DIRECT 면 답변 직접 생성).
answer: BE 가 검색한 context.reports 근거로 답변 생성.
"""

from __future__ import annotations

from app.config import get_settings
from app.core.structured import complete_structured
from app.prompts.chatbot import build_answer_messages, build_plan_messages
from app.schemas.chatbot import (
    ChatAnswerRequest,
    ChatAnswerResult,
    ChatPlanRequest,
    ChatPlanResult,
)


async def plan(req: ChatPlanRequest) -> ChatPlanResult:
    settings = get_settings()
    messages = build_plan_messages(
        question=req.question,
        history=req.history,
        has_location=req.userLocation is not None,
        limit=settings.chatbot_history_max_turns,
    )
    return await complete_structured(
        messages=messages,
        schema=ChatPlanResult,
        temperature=0.0,  # deterministic routing
    )


async def answer(req: ChatAnswerRequest) -> ChatAnswerResult:
    settings = get_settings()
    messages = build_answer_messages(
        question=req.question,
        history=req.history,
        context=req.context,
        limit=settings.chatbot_history_max_turns,
    )
    return await complete_structured(
        messages=messages,
        schema=ChatAnswerResult,
        temperature=settings.chatbot_answer_temperature,
    )
