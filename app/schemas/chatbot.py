"""③ 챗봇 2-스텝 스키마 (plan / answer).

각 Result 모델은 LLM Structured Output 스키마이자 API 응답 모델로 함께 쓰인다.
LLM 출력 필드는 모두 required (기본값 금지), nullable 은 `X | None`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.core.taxonomy import CategoryCode


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class UserLocation(BaseModel):
    lat: float
    lng: float


# --- Step 1: plan -------------------------------------------------------------
class ChatAction(StrEnum):
    ANSWER_DIRECT = "ANSWER_DIRECT"
    SEARCH_NEARBY = "SEARCH_NEARBY"
    MY_REPORTS = "MY_REPORTS"


class PlanParams(BaseModel):
    categoryCode: CategoryCode | None
    radiusMeters: int | None


class ChatPlanRequest(BaseModel):
    question: str
    history: list[ChatMessage] = Field(default_factory=list)
    userLocation: UserLocation | None = None


class ChatPlanResult(BaseModel):
    """LLM 출력 = 응답. ANSWER_DIRECT 면 answer 채움, 그 외엔 params 채우고 answer=null."""

    action: ChatAction
    params: PlanParams
    answer: str | None


# --- Step 2: answer -----------------------------------------------------------
class ContextReport(BaseModel):
    reportId: int
    title: str
    summary: str
    category: str | None = None
    address: str | None = None
    riskScore: float | None = None
    distanceMeters: float | None = None
    recentReportedAt: str | None = None


class ChatContext(BaseModel):
    scope: str
    reports: list[ContextReport] = Field(default_factory=list)
    userLocation: UserLocation | None = None


class ChatAnswerRequest(BaseModel):
    question: str
    history: list[ChatMessage] = Field(default_factory=list)
    context: ChatContext


class ChatAnswerResult(BaseModel):
    """LLM 출력 = 응답. 근거(context.reports)에 있는 사실만 사용."""

    answer: str
    usedReportIds: list[int]
