"""Similar public complaint service for the future RAG pipeline."""

from __future__ import annotations

import logging

from app.schemas.public_complaint import SimilarComplaintCase
from app.services import public_complaint_client

logger = logging.getLogger("ssairen.similar_complaint")


async def search_similar_cases(user_text: str) -> list[SimilarComplaintCase]:
    """Return normalized similar public complaint cases for a user report text."""
    try:
        api_items = await public_complaint_client.fetch_similar_complaints(user_text)
    except Exception as exc:
        logger.warning("Similar complaint normalization failed: %s", exc.__class__.__name__)
        return []

    cases: list[SimilarComplaintCase] = []
    for item in api_items:
        case = SimilarComplaintCase.from_api_item(item)
        if case is not None:
            cases.append(case)
    return cases
