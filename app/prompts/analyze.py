"""① 구조화 분석 프롬프트.

시스템 프롬프트는 택소노미 SSOT(few-shot + 타이브레이크)를 단일 소스로 주입한다.
"""

from __future__ import annotations

from app.core.taxonomy import few_shot_block


def get_system_prompt() -> str:
    return f"""당신은 '싸이렌'의 제보 분석 AI입니다.
시민이 보낸 사진·텍스트·위치를 분석해 구조화된 제보 데이터를 한국어로 생성합니다.
모든 출력은 주어진 JSON 스키마를 정확히 따릅니다.

[카테고리 분류]
- categoryCode 는 아래 목록에서 정확히 하나만 선택합니다. 목록에 없는 값을 만들지 마세요.
- 유효하나 기존 유형에 맞지 않으면 ETC_OTHER, 내용·이미지가 불충분/무관/확인불가하여
  제보로 성립하지 않으면 INSUFFICIENT 로 분류합니다(억지 분류 금지).
- confidence 는 0.0~1.0 사이 확신도입니다.

{few_shot_block()}

[위험도] riskScore 는 0~100:
- 0~20 참고, 20~40 낮음, 40~60 보통, 60~80 높음, 80~100 긴급.
- 카테고리 위험성, 사진 속 심각도, 즉시성(사람·차량 위해 가능성)을 종합합니다.

[허위·장난 탐지] analysis.falseReport:
- isSuspicious: 이미지-텍스트 불일치, 욕설/장난성, 무관 이미지, 조작 의심 시 true.
- score: 0~100 허위 의심 점수(높을수록 의심). reason: 판단 사유 한 문장.

[긴급 안내] analysis.emergencyGuide:
- 실제 화재·연기·가스누출 등은 isEmergency=true, message 에 "즉시 119에 신고하세요" 류 안내.
- 진행 중 범죄·폭력·응급환자는 isEmergency=true, message 에 112/119 안내.
- 그 외에는 isEmergency=false, message=null.

[육하원칙] contents 의 who/when/where/what/how/why/summary 를 모두 채웁니다.
- 모르면 "확인되지 않음". where 는 제공된 주소 정보를 활용합니다. when 은 발생 시각을 사용합니다.
- summary 는 상황을 한 문장으로 요약합니다.

[제목·키워드] title 은 제보를 요약한 한 줄 제목(따옴표 없이). keywords 는 핵심 키워드 3~6개.

[객체 인식] analysis.detectedObjects: 사진에서 보이는 핵심 객체(도로/쓰레기/차량/사람/파손 등).
사진이 없으면 빈 배열.

추측을 사실로 단정하지 말고, 사진과 텍스트에서 확인되는 범위로 기술하세요."""


def build_messages(
    *,
    content: str,
    occurred_at: str,
    latitude: float,
    longitude: float,
    road_address: str | None = None,
    sido: str | None = None,
    sigungu: str | None = None,
    eupmyeondong: str | None = None,
    image_data_urls: list[str],
) -> list[dict]:
    """system + user(멀티모달) 메시지 구성."""
    address_lines = []
    if road_address:
        address_lines.append(f"- 도로명주소: {road_address}")
    if sido or sigungu or eupmyeondong:
        admin = " ".join(x for x in (sido, sigungu, eupmyeondong) if x)
        address_lines.append(f"- 행정구역: {admin}")
    address_block = "\n".join(address_lines) if address_lines else "- (주소 정보 없음)"

    user_text = f"""[원문 제보]
{content}

[발생 시각]
{occurred_at}

[위치]
- 좌표: {latitude}, {longitude}
{address_block}

위 정보와 첨부 사진을 분석해 스키마에 맞는 구조화 제보를 생성하세요."""

    user_content: list[dict] = [{"type": "text", "text": user_text}]
    for url in image_data_urls:
        user_content.append({"type": "image_url", "image_url": {"url": url}})

    return [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_content},
    ]
