"""분류 프롬프트 — 1차(대분류)·2차(소분류).

택소노미 SSOT(`core/taxonomy.py`)의 블록을 단일 소스로 주입한다.
"""

from __future__ import annotations

from app.core import taxonomy
from app.core.taxonomy import MAJOR_KO, MajorCategory
from app.prompts.common import build_report_context, multimodal_user_content


def build_major_messages(
    *,
    content: str,
    occurred_at: str,
    location_block: str,
    image_data_urls: list[str],
) -> list[dict]:
    """1차: 대분류 1개 선택 + 제보 불성립 판정."""
    system = f"""당신은 '싸이렌'의 제보 분류 AI입니다. 1단계로 **대분류 하나**만 고릅니다.
시민이 보낸 사진·텍스트·위치를 보고 아래 목록에서 majorCode 를 정확히 하나 선택하세요.

[대분류 목록]
{taxonomy.major_block()}

- confidence 는 0.0~1.0 확신도입니다.
- insufficient: 내용·이미지가 불충분/무관/확인 불가하여 처리 가능한 제보로 성립하지 않으면 true.
  이때 majorCode 는 ETC 로 둡니다. (장난·허위는 여기서 거르지 말고 후속 단계가 판단)
- 유효하나 어느 대분류에도 맞지 않으면 ETC 를 선택하되 insufficient 는 false 로 둡니다."""

    user_text = build_report_context(
        content=content, occurred_at=occurred_at, location_block=location_block
    ) + "\n\n위 제보의 대분류를 선택하세요."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": multimodal_user_content(user_text, image_data_urls)},
    ]


def build_minor_messages(
    *,
    major: MajorCategory,
    content: str,
    occurred_at: str,
    location_block: str,
    image_data_urls: list[str],
) -> list[dict]:
    """2차: 확정된 대분류 안에서 소분류 1개 선택."""
    system = f"""당신은 '싸이렌'의 제보 분류 AI입니다. 2단계로 **소분류 하나**만 고릅니다.
1단계에서 대분류는 '{major.value}({MAJOR_KO[major]})'로 확정되었습니다.
아래 소분류 목록에서 minorCode 를 정확히 하나 선택하세요(목록 밖 값 금지).

[소분류 목록]
{taxonomy.minor_block(major)}

- 어느 소분류에도 맞지 않으면 ETC_OTHER 를 선택합니다(억지 분류 금지).
- confidence 는 0.0~1.0 확신도입니다."""

    user_text = build_report_context(
        content=content, occurred_at=occurred_at, location_block=location_block
    ) + f"\n\n위 제보의 소분류를 '{major.value}' 안에서 선택하세요."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": multimodal_user_content(user_text, image_data_urls)},
    ]
