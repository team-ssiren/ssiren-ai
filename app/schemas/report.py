"""① 구조화 분석 스키마.

`API 명세서(AI-BE).md` 의 응답 계약과 1:1 (camelCase). LLM 은 임베딩을 제외한
`AnalysisLLMOutput` 을 Structured Output(enum 강제)으로 생성하고, 서버가 임베딩을
합성해 `AnalyzeResponse` 로 반환한다.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.taxonomy import CategoryCode


class FiveW1H(BaseModel):
    who: str
    when: str
    where: str
    what: str
    how: str
    why: str
    summary: str


class CategoryResult(BaseModel):
    categoryCode: CategoryCode
    confidence: float  # 0.0 ~ 1.0


class FalseReport(BaseModel):
    isSuspicious: bool
    score: float  # 0 ~ 100 (높을수록 허위 의심)
    reason: str


class EmergencyGuide(BaseModel):
    isEmergency: bool
    message: str | None  # 긴급 시 안내 문구, 아니면 null


class Analysis(BaseModel):
    detectedObjects: list[str]
    falseReport: FalseReport
    emergencyGuide: EmergencyGuide


class AnalysisLLMOutput(BaseModel):
    """LLM 이 Structured Output 으로 생성하는 부분 (임베딩 제외).

    모든 필드는 required (기본값 금지) — OpenAI strict structured outputs 규약.
    nullable 은 `X | None` 으로 표현.
    """

    title: str
    contents: FiveW1H
    keywords: list[str]
    category: CategoryResult
    riskScore: float  # 0 ~ 100
    analysis: Analysis


class AnalyzeResponse(AnalysisLLMOutput):
    """API 응답 = LLM 출력 + 서버가 합성한 필드."""

    # 서버가 해소한 발생 시각(요청값 또는 서버 기본값). contents.when 과 동일 출처라
    # BE 는 이 값을 reportDraft.occurredAt 으로 그대로 사용하면 일관된다.
    occurredAt: str
    embedding: list[float]
