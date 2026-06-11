"""Data.go.kr similar public complaint API client."""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.schemas.public_complaint import PublicComplaintApiItem, PublicComplaintApiResponse

logger = logging.getLogger("ssairen.public_complaint")

SIMILAR_INFO_URL = "https://apis.data.go.kr/1140100/minAnalsInfoView5/minSimilarInfo5"
TIMEOUT_SECONDS = 3.0
START_POS = 1
RET_COUNT = 100
TARGET = "qna,qna_origin"
DATA_TYPE = "json"


async def fetch_similar_complaints(user_text: str) -> list[PublicComplaintApiItem]:
    """Fetch raw similar complaint items from Data.go.kr.

    Failures are intentionally swallowed so the report draft pipeline can
    continue without public-data RAG context.
    """
    searchword = user_text.strip() if user_text else ""
    if not searchword:
        return []

    settings = get_settings()
    if not settings.data_gokr_api_key:
        logger.warning("Data.go.kr API key is not configured; skip similar complaint lookup")
        return []

    params = {
        "serviceKey": settings.data_gokr_api_key,
        "startPos": START_POS,
        "retCount": RET_COUNT,
        "searchword": searchword,
        "target": TARGET,
        "dataType": DATA_TYPE,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(SIMILAR_INFO_URL, params=params)
        if response.status_code >= 400:
            logger.warning(
                "Data.go.kr similar complaint lookup failed. status=%s",
                response.status_code,
            )
            return []
        if not response.content:
            logger.warning("Data.go.kr similar complaint lookup returned empty body")
            return []

        payload = response.json()
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning(
            "Data.go.kr similar complaint lookup request failed: %s",
            exc.__class__.__name__,
        )
        return []
    except ValueError:
        logger.warning("Data.go.kr similar complaint lookup returned invalid JSON")
        return []

    return PublicComplaintApiResponse.from_payload(payload).items
