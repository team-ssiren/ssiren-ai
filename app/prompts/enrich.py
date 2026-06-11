"""보강(3차) 프롬프트 — 구조화 아웃풋 + 담당 부서 결정.

확정된 대/소분류 + 할당 가이드(평문) + 유사 민원 사례 + 후보 부서 목록을 컨텍스트로
주입해, 5W1H·위험도·허위탐지·긴급안내 + suggestedDepartment 를 생성한다.
기관유형은 부서에서 결정론적으로 도출하므로 LLM 이 별도로 출력하지 않는다.
"""

from __future__ import annotations

from app.core.taxonomy import MAJOR_KO, MajorCategory, get_leaf
from app.db.repository import DepartmentRow
from app.prompts.common import build_report_context, multimodal_user_content
from app.schemas.public_complaint import RankedSimilarComplaintCase

SIMILAR_COMPLAINT_CONTENT_MAX_CHARS = 500


def _system_prompt() -> str:
    return """당신은 '싸이렌'의 제보 분석 AI입니다. 대분류·소분류가 이미 확정되었습니다.
제공된 '기관·부서 배정 근거자료'와 '유사 민원 사례', 그리고 '선택 가능한 부서 후보'를 근거로
구조화된 제보 데이터와 담당 부서를 한국어로 생성합니다. 출력은 JSON 스키마를 정확히 따릅니다.

[위험도] riskScore 0~100: 0~20 참고, 20~40 낮음, 40~60 보통, 60~80 높음, 80~100 긴급.
카테고리 위험성·사진 속 심각도·즉시성(사람·차량 위해 가능성)을 종합합니다.

[허위·장난 탐지] analysis.falseReport:
- isSuspicious: 이미지-텍스트 불일치, 욕설/장난성, 무관 이미지, 조작 의심 시 true.
- score: 0~100 허위 의심 점수. reason: 판단 사유 한 문장.

[긴급 안내] analysis.emergencyGuide:
- 실제 화재·연기·가스누출은 isEmergency=true, message 에 "즉시 119에 신고하세요" 류.
- 진행 중 범죄·폭력·응급환자는 isEmergency=true, message 에 112/119 안내.
- 그 외 isEmergency=false, message=null.

[육하원칙] contents 의 who/when/where/what/how/why/summary 를 모두 채웁니다.
모르면 "확인되지 않음". where 는 제공된 주소를, when 은 발생 시각을 활용합니다.

[제목·키워드] title 은 한 줄 제목(따옴표 없이). keywords 는 핵심 3~6개.
[객체 인식] analysis.detectedObjects: 사진 속 핵심 객체. 사진이 없으면 빈 배열.

[담당 부서 배정]
- suggestedDepartment 는 반드시 '선택 가능한 부서 후보' 중에서 고릅니다
  (후보가 없으면 가장 적합한 부서명). 배정 근거자료와 유사 민원의 실제 담당 부서를
  종합해 역할이 가장 가까운 부서를 선택합니다. (기관유형은 부서에서 자동 도출되므로
  별도로 출력하지 않습니다.)

[assignmentReason — 배정 근거 작성 규칙]
이 기관·부서로 배정한 **확정적 근거**를 따박따박 적습니다. 다음을 반드시 지키세요:
- 단정적으로 씁니다. "~일 수 있다/~할 수도/아마/추정/~로 보인다" 같은 추측·완곡 표현 금지.
- "가이드에 따르면/자료상/사례가 제공되어" 같은 출처·메타 언급 금지. 근거의 '내용'을
  사실로 직접 기술합니다.
- "선택 가능한 부서 중/후보 부서 중에서" 같은 후보 목록 언급 금지. 선택한 부서의 소관
  업무를 단정적으로 기술합니다(예: "…는 분당구청 건설과의 소관 사무이다").
- 다음 항목을 가능한 한 모두, 구체적으로 제시합니다:
  ① 법령 근거 — 구체 법률명·조항(예: 하수도법 제3조). 관할·소관 주체를 명시.
  ② 해당 부서가 그 업무를 담당하는 이유(부서의 소관 업무로 연결).
  ③ 유사 민원의 실제 처리 부서명을 인용(있을 때).
- 법률명·조항·기관·부서명은 제공된 배정 근거자료와 유사 민원에 실제로 등장하는 것만
  사용합니다. 없는 조항·기관을 지어내지 마세요(허위 인용 금지).
- 예: "맨홀·빗물받이 등 공공하수도 시설의 유지관리는 하수도법 제3조에 따라 공공하수도
  관리청인 분당구청의 책무이다. 도로상 맨홀 파손의 임시 안전조치 및 시설 보수는 분당구청
  건설과의 소관 업무이며, 유사 민원에서도 도로·시설 유지관리 부서가 동일 사안을 처리하였다."

추측을 사실로 단정하지 말고, 사진·텍스트에서 확인되는 범위로 기술하세요."""


def build_enrich_messages(
    *,
    major: MajorCategory,
    minor_code: str,
    content: str,
    occurred_at: str,
    location_block: str,
    image_data_urls: list[str],
    guide_text: str | None,
    similar_complaints: list[RankedSimilarComplaintCase],
    candidates: list[DepartmentRow],
) -> list[dict]:
    leaf = get_leaf(minor_code)
    category_line = (
        f"[확정 분류]\n- 대분류: {major.value}({MAJOR_KO[major]})"
        f"\n- 소분류: {minor_code}({leaf.ko}) — {leaf.definition}"
    )
    guide_block = _guide_block(guide_text)
    similar_block = _similar_block(similar_complaints)
    candidate_block = _candidate_block(candidates)

    user_text = "\n\n".join(
        part
        for part in (
            build_report_context(
                content=content, occurred_at=occurred_at, location_block=location_block
            ),
            category_line,
            guide_block,
            similar_block,
            candidate_block,
            "위 정보를 종합해 스키마에 맞는 구조화 제보와 담당 기관·부서를 생성하세요.",
        )
        if part
    )
    return [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": multimodal_user_content(user_text, image_data_urls)},
    ]


def _guide_block(guide_text: str | None) -> str:
    if not guide_text:
        return ""
    return f"[기관·부서 배정 근거자료]\n{guide_text.strip()}"


def _candidate_block(candidates: list[DepartmentRow]) -> str:
    if not candidates:
        return ""
    lines = ["[선택 가능한 부서 후보]"]
    for c in candidates:
        lines.append(f"- {c.department} (기관: {c.agency_name}, 유형: {c.agency_type})")
    return "\n".join(lines)


def _similar_block(similar_complaints: list[RankedSimilarComplaintCase]) -> str:
    if not similar_complaints:
        return ""
    lines = ["[공공데이터 유사 민원 사례 TOP5]"]
    for index, case in enumerate(similar_complaints, start=1):
        lines.extend(
            [
                f"{index}. title: {_truncate(case.title, 150)}",
                f"   content: {_truncate(case.content, SIMILAR_COMPLAINT_CONTENT_MAX_CHARS)}",
                f"   mainSubName: {case.mainSubName}",
                f"   departmentName: {case.departmentName}",
                f"   similarityScore: {case.embeddingScore:.4f}",
            ]
        )
    return "\n".join(lines)


def _truncate(value: str, max_chars: int) -> str:
    if value is None:
        return ""
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "..."
