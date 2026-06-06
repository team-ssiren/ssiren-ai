"""① 구조화 분석 엔드포인트 — POST /internal/v1/reports:analyze (multipart).

BE 가 멀티파트로 이미지 바이트 + 텍스트 + (역지오코딩한) 주소를 보내면 구조화 분석
결과를 반환한다. 이미지는 개수·용량·MIME 가드를 거친다.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.schemas.report import AnalyzeResponse
from app.services import analyzer
from app.services.analyzer import AnalyzeInput, ImageInput

router = APIRouter(prefix="/internal/v1", tags=["reports"])


@router.post("/reports:analyze", response_model=AnalyzeResponse)
async def analyze_report(
    content: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    occurredAt: str | None = Form(default=None),
    roadAddress: str | None = Form(default=None),
    sido: str | None = Form(default=None),
    sigungu: str | None = Form(default=None),
    eupmyeondong: str | None = Form(default=None),
    images: list[UploadFile] = File(default=[]),
) -> AnalyzeResponse:
    settings = get_settings()

    if len(images) > settings.analyze_max_images:
        raise HTTPException(
            status_code=422,
            detail=f"too many images: {len(images)} > {settings.analyze_max_images}",
        )

    max_bytes = settings.analyze_max_image_mb * 1024 * 1024
    image_inputs: list[ImageInput] = []
    for f in images:
        if f.content_type and not f.content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail=f"unsupported file type: {f.content_type}")
        data = await f.read()
        if not data:
            continue  # tolerate empty multipart slots
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"image too large: > {settings.analyze_max_image_mb}MB",
            )
        image_inputs.append(ImageInput(data=data, content_type=f.content_type or "image/jpeg"))

    return await analyzer.analyze(
        AnalyzeInput(
            content=content,
            latitude=latitude,
            longitude=longitude,
            occurred_at=occurredAt,
            road_address=roadAddress,
            sido=sido,
            sigungu=sigungu,
            eupmyeondong=eupmyeondong,
            images=image_inputs,
        )
    )
