"""③ 챗봇 프롬프트 — plan(의도 라우팅) / answer(근거 기반 생성)."""

from __future__ import annotations

from app.core.taxonomy import leaf_codes
from app.schemas.chatbot import ChatContext, ChatMessage


def _history_to_messages(history: list[ChatMessage], limit: int) -> list[dict]:
    recent = history[-limit:] if limit > 0 else history
    return [{"role": m.role, "content": m.content} for m in recent]


# --- Step 1: plan -------------------------------------------------------------
PLAN_SYSTEM = f"""당신은 '싸이렌'(지역 안전 제보 앱) 챗봇의 의도 라우터입니다.
사용자의 질문과 대화 맥락을 보고 다음 action 중 하나를 고릅니다.

- ANSWER_DIRECT: 서비스 일반 질문·잡담 등 제보 데이터 검색이 필요 없는 경우.
  이 경우 answer 에 한국어 답변을 직접 작성하고, params 의 모든 값은 null 입니다.
- SEARCH_NEARBY: "이 근처 위험한 제보 있어?"처럼 주변 제보 검색이 필요한 경우.
  params.radiusMeters(기본 500) 와, 특정 유형을 물으면 params.categoryCode 를 채웁니다.
  answer 는 null 입니다.
- MY_REPORTS: "내 제보 어떻게 됐어?"처럼 사용자 본인 제보 조회가 필요한 경우.
  params 는 모두 null, answer 도 null 입니다(BE 가 본인 제보를 조회·응답).

params.categoryCode 는 다음 중 하나이거나 null: {", ".join(leaf_codes())}.
사용하지 않는 params 필드는 null 로 둡니다.

[긴급] 사용자가 진행 중인 화재·범죄·응급 상황을 묘사하면 ANSWER_DIRECT 로,
answer 에 즉시 112(범죄)/119(화재·응급) 신고를 우선 안내하세요."""


def build_plan_messages(
    question: str, history: list[ChatMessage], has_location: bool, limit: int
) -> list[dict]:
    loc = (
        "사용자 위치 정보가 제공됨."
        if has_location
        else "사용자 위치 정보 없음(SEARCH_NEARBY 시 BE가 처리)."
    )
    messages: list[dict] = [{"role": "system", "content": PLAN_SYSTEM}]
    messages += _history_to_messages(history, limit)
    messages.append({"role": "user", "content": f"[{loc}]\n{question}"})
    return messages


# --- Step 2: answer -----------------------------------------------------------
ANSWER_SYSTEM = """당신은 '싸이렌'(지역 안전 제보 앱)의 챗봇입니다.
아래 제공된 '제보 목록'에 있는 사실만 근거로 한국어로 친절하게 답합니다.

[근거 고정 규칙]
- 제공된 제보에 없는 내용을 지어내지 마세요.
- 제보 목록이 비어 있으면 "주변에 접수된 제보가 없어요" 처럼 솔직하게 답합니다.
- 답변에 실제로 활용한 제보의 reportId 만 usedReportIds 에 담습니다(활용 안 했으면 빈 배열).
- 거리·위험도 등 수치가 있으면 자연스럽게 활용합니다.

[긴급] 사용자가 진행 중인 화재·범죄·응급 상황을 묘사하면 112/119 신고를 우선 안내하세요."""


def _format_reports(context: ChatContext) -> str:
    if not context.reports:
        return "(제보 목록 없음)"
    lines = []
    for r in context.reports:
        bits = [f"[reportId={r.reportId}] {r.title}"]
        if r.category:
            bits.append(f"유형={r.category}")
        if r.address:
            bits.append(f"위치={r.address}")
        if r.distanceMeters is not None:
            bits.append(f"거리={round(r.distanceMeters)}m")
        if r.riskScore is not None:
            bits.append(f"위험도={r.riskScore}")
        if r.recentReportedAt:
            bits.append(f"최근={r.recentReportedAt}")
        line = " · ".join(bits)
        if r.summary:
            line += f"\n    요약: {r.summary}"
        lines.append(line)
    return "\n".join(lines)


def build_answer_messages(
    question: str, history: list[ChatMessage], context: ChatContext, limit: int
) -> list[dict]:
    context_block = f"[제보 목록 · scope={context.scope}]\n{_format_reports(context)}"
    messages: list[dict] = [
        {"role": "system", "content": ANSWER_SYSTEM},
        {"role": "system", "content": context_block},
    ]
    messages += _history_to_messages(history, limit)
    messages.append({"role": "user", "content": question})
    return messages
