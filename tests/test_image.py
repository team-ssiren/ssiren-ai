"""Image downscaling for the OpenAI vision request."""

import io

import pytest
from PIL import Image

from app.core.errors import InvalidImageError
from app.core.image import downscale_to_max_pixels, to_data_url

MAX = 1_000_000


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (100, 120, 140)).save(buf, format="PNG")
    return buf.getvalue()


def test_within_budget_returned_unchanged():
    data = _png(100, 100)  # 10k px <= 1M
    out, ctype = downscale_to_max_pixels(data, "image/png", MAX)
    assert out == data
    assert ctype == "image/png"


def test_oversized_is_downscaled_to_budget_and_jpeg():
    data = _png(2000, 2000)  # 4M px > 1M
    out, ctype = downscale_to_max_pixels(data, "image/png", MAX)
    assert ctype == "image/jpeg"
    with Image.open(io.BytesIO(out)) as img:
        w, h = img.size
    assert w * h <= MAX
    assert abs(w - h) <= 1  # aspect ratio (square) preserved


def test_aspect_ratio_preserved_for_wide_image():
    data = _png(4000, 1000)  # 4M px, 4:1
    out, _ = downscale_to_max_pixels(data, "image/png", MAX)
    with Image.open(io.BytesIO(out)) as img:
        w, h = img.size
    assert w * h <= MAX
    assert abs((w / h) - 4.0) < 0.05


def test_invalid_image_raises():
    with pytest.raises(InvalidImageError):
        downscale_to_max_pixels(b"\xff\xd8\xff not an image", "image/jpeg", MAX)


def test_to_data_url_prefix():
    url = to_data_url(_png(10, 10), "image/png", MAX)
    assert url.startswith("data:image/png;base64,")
