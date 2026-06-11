"""Similar public complaint service for the future RAG pipeline."""

from __future__ import annotations

import logging
import math

from app.config import get_settings
from app.schemas.public_complaint import RankedSimilarComplaintCase, SimilarComplaintCase
from app.services import embedder, public_complaint_client

logger = logging.getLogger("ssairen.similar_complaint")

MIN_SIMILARITY_SCORE = 0.50
TOP_K = 5


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


async def find_top_similar_cases(user_text: str) -> list[RankedSimilarComplaintCase]:
    """Return TOP-K public complaint cases ranked by embedding cosine similarity."""
    query_text = user_text.strip() if user_text else ""
    if not query_text:
        return []

    cases = await search_similar_cases(query_text)
    if not cases:
        return []

    texts = [query_text, *[case.embeddingText for case in cases]]
    try:
        embeddings = await _embed_all(texts)
    except Exception as exc:
        logger.warning("Similar complaint embedding failed: %s", exc.__class__.__name__)
        return []

    if len(embeddings) != len(texts):
        logger.warning(
            "Similar complaint embedding count mismatch. expected=%d actual=%d",
            len(texts),
            len(embeddings),
        )
        return []

    query_embedding = embeddings[0]
    ranked_cases: list[RankedSimilarComplaintCase] = []
    for case, case_embedding in zip(cases, embeddings[1:], strict=True):
        score = cosine_similarity(query_embedding, case_embedding)
        if score is None or score < MIN_SIMILARITY_SCORE:
            continue
        ranked_cases.append(RankedSimilarComplaintCase.from_case(case, score))

    return sorted(ranked_cases, key=lambda case: case.embeddingScore, reverse=True)[:TOP_K]


async def _embed_all(texts: list[str]) -> list[list[float]]:
    cleaned_texts = [text.strip() for text in texts if text and text.strip()]
    if len(cleaned_texts) != len(texts):
        logger.warning("Similar complaint embedding input contains blank text")
        return []

    settings = get_settings()
    batch_size = max(1, settings.embedding_max_batch)
    vectors: list[list[float]] = []
    for start in range(0, len(cleaned_texts), batch_size):
        vectors.extend(await embedder.embed(cleaned_texts[start : start + batch_size]))
    return vectors


def cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if not left or not right or len(left) != len(right):
        return None

    try:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
    except (TypeError, ValueError, OverflowError):
        return None

    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)
