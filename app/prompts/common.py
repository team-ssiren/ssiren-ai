"""프롬프트 공통 빌더 — 위치/시각 컨텍스트 + 멀티모달 user content."""

from __future__ import annotations


def build_location_block(
    *,
    latitude: float,
    longitude: float,
    road_address: str | None,
    sido: str | None,
    sigungu: str | None,
    eupmyeondong: str | None,
) -> str:
    lines = [f"- 좌표: {latitude}, {longitude}"]
    if road_address:
        lines.append(f"- 도로명주소: {road_address}")
    if sido or sigungu or eupmyeondong:
        admin = " ".join(x for x in (sido, sigungu, eupmyeondong) if x)
        lines.append(f"- 행정구역: {admin}")
    if len(lines) == 1:
        lines.append("- (상세 주소 정보 없음)")
    return "\n".join(lines)


def build_report_context(
    *,
    content: str,
    occurred_at: str,
    location_block: str,
) -> str:
    return f"""[원문 제보]
{content}

[발생 시각]
{occurred_at}

[위치]
{location_block}"""


def multimodal_user_content(text: str, image_data_urls: list[str]) -> list[dict]:
    """text 파트 + 이미지 파트들로 구성된 user content."""
    parts: list[dict] = [{"type": "text", "text": text}]
    for url in image_data_urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts
