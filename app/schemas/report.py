"""① 구조화 분석 스키마 (응답 계약, camelCase).

다단계 파이프라인이 단계별로 채운 값을 서버가 조립해 `AnalyzeResponse` 로 반환한다:
- category(대/소분류)·analysis·기관/부서 추천은 LLM(1~3차) 산출
- embedding 은 서버가 합성, resolvedAgency 는 SQLite 조직표에서 해소
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.taxonomy import CategoryCode, MajorCategory


class FiveW1H(BaseModel):
    who: str
    when: str
    where: str
    what: str
    how: str
    why: str
    summary: str


class CategoryResult(BaseModel):
    majorCode: MajorCategory
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


class ResolvedAgency(BaseModel):
    """배정된 기관·부서.

    department/agencyType 는 AI 가 결정한 값(후보 부서로 enum 제약)을 항상 담는다.
    name/phone 은 조직표에서 해소되면 채워지고, 못 찾으면 null(resolved=False).
    """

    agencyType: str | None  # 기관유형 (부서 행에서 도출)
    department: str | None  # 최하위기관명 e.g. 건설과 (AI 결정)
    name: str | None  # 전체기관명 e.g. 분당구청 (해소 시)
    phone: str | None  # 부서 전화(없으면 기관 전화)
    resolved: bool  # 조직표에서 실제 기관 행을 찾았는지


class AnalysisLLMOutput(BaseModel):
    """LLM(1~3차)이 결정한 분석 본문 (임베딩/조직표 해소 제외)."""

    title: str
    contents: FiveW1H
    keywords: list[str]
    category: CategoryResult
    riskScore: float  # 0 ~ 100
    analysis: Analysis
    assignmentReason: str  # 이 부서로 배정한 근거(가이드·유사사례·법령 기반)


class AnalyzeResponse(AnalysisLLMOutput):
    """API 응답 = 분석 본문 + 서버 합성/해소 필드."""

    occurredAt: str
    embedding: list[float]
    resolvedAgency: ResolvedAgency
