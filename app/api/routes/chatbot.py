"""③ 챗봇 엔드포인트 — POST /internal/v1/chatbot:plan, :answer."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.chatbot import (
    ChatAnswerRequest,
    ChatAnswerResult,
    ChatPlanRequest,
    ChatPlanResult,
)
from app.services import chatbot

router = APIRouter(prefix="/internal/v1", tags=["chatbot"])


@router.post("/chatbot:plan", response_model=ChatPlanResult)
async def chatbot_plan(req: ChatPlanRequest) -> ChatPlanResult:
    return await chatbot.plan(req)


@router.post("/chatbot:answer", response_model=ChatAnswerResult)
async def chatbot_answer(req: ChatAnswerRequest) -> ChatAnswerResult:
    return await chatbot.answer(req)
