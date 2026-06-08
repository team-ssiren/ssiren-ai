"""이미지 전처리 — OpenAI 비전 호출 전 다운스케일.

업로드는 최대 50MB 까지 허용하되, 실제 OpenAI 요청에는 픽셀 수를 상한(기본 1M px)으로
줄여 비용·지연을 낮춘다. 상한 이내 이미지는 원본 그대로 사용한다.
"""

from __future__ import annotations

import base64
import io

from PIL import Image, UnidentifiedImageError

from app.core.errors import InvalidImageError


def downscale_to_max_pixels(
    data: bytes, content_type: str, max_pixels: int
) -> tuple[bytes, str]:
    """`max_pixels` 초과 시 종횡비 유지하며 축소 후 JPEG 재인코딩.

    상한 이내면 (원본 bytes, 원본 content_type) 그대로 반환.
    디코딩 실패 시 InvalidImageError(422).
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            width, height = img.size
            pixels = width * height
            if pixels <= max_pixels:
                return data, content_type
            scale = (max_pixels / pixels) ** 0.5
            new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            resized = img.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError(f"cannot decode image: {exc}") from exc

    buf = io.BytesIO()
    resized.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"


def to_data_url(data: bytes, content_type: str, max_pixels: int) -> str:
    """다운스케일 후 base64 data URL 로 변환(OpenAI image_url 용)."""
    scaled, ctype = downscale_to_max_pixels(data, content_type, max_pixels)
    b64 = base64.b64encode(scaled).decode("ascii")
    return f"data:{ctype};base64,{b64}"
