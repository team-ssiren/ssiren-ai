"""Similar public complaint service for the future RAG pipeline."""

from __future__ import annotations

import logging
import math
from datetime import datetime

from app.config import get_settings
from app.schemas.public_complaint import RankedSimilarComplaintCase, SimilarComplaintCase
from app.services import embedder, public_complaint_client

logger = logging.getLogger("ssairen.similar_complaint")

MIN_SIMILARITY_SCORE = 0.50
TOP_K = 5
EMBEDDING_SCORE_WEIGHT = 80.0
RECENCY_SCORE_WEIGHT = 10.0
DEPARTMENT_SCORE_BONUS = 10.0
RECENCY_FULL_SCORE_DAYS = 365
RECENCY_MEDIUM_SCORE_DAYS = 365 * 3
RECENCY_LOW_SCORE_DAYS = 365 * 5
DEPARTMENT_BONUS_PATTERNS = (
    "건설과",
    "구조물관리과",
    "경제교통과",
    "환경자원과",
    "도시미관과",
    "건축과",
    "위생안전과",
    "녹지공원과",
    "보건행정과",
    "건강증진과",
    "감염병관리센터",
    "사회복지과",
    "가정복지과",
    "소방행정과",
    "재난대응과",
    "화재예방과",
    "현장지휘단",
    "119구조대",
    "경비교통과",
    "범죄예방대응과",
    "여성청소년과",
    "형사과",
    "수사과",
    "치안정보안보과",
    "경무과",
    "청문감사인권관",
    "청문인권담당관",
    "판교보건지소",
    "119안전센터",
    "지구대",
    "파출소",
)


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
    now = datetime.now()
    for case, case_embedding in zip(cases, embeddings[1:], strict=True):
        score = cosine_similarity(query_embedding, case_embedding)
        if score is None or score < MIN_SIMILARITY_SCORE:
            continue
        recency_score = calculate_recency_score(case.createDate, now)
        department_score = calculate_department_score(case.departmentName)
        rerank_score = calculate_rerank_score(score, recency_score, department_score)
        logger.info(
            "Similar complaint rerank candidate. embeddingScore=%.4f recencyScore=%.2f "
            "departmentScore=%.2f rerankScore=%.2f title=%s department=%s",
            score,
            recency_score,
            department_score,
            rerank_score,
            _preview(case.title),
            _preview(case.departmentName),
        )
        ranked_cases.append(
            RankedSimilarComplaintCase.from_case(
                case,
                score,
                recency_score,
                department_score,
                rerank_score,
            )
        )

    top_cases = sorted(ranked_cases, key=lambda case: case.rerankScore, reverse=True)[:TOP_K]
    for index, case in enumerate(top_cases, start=1):
        logger.info(
            "Similar complaint rerank TOP%d. rerankScore=%.2f embeddingScore=%.4f "
            "recencyScore=%.2f departmentScore=%.2f title=%s department=%s",
            index,
            case.rerankScore,
            case.embeddingScore,
            case.recencyScore,
            case.departmentScore,
            _preview(case.title),
            _preview(case.departmentName),
        )
    return top_cases


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


def calculate_rerank_score(
    embedding_score: float,
    recency_score: float,
    department_score: float,
) -> float:
    return embedding_score * EMBEDDING_SCORE_WEIGHT + recency_score + department_score


def calculate_recency_score(create_date: datetime | None, now: datetime | None = None) -> float:
    if create_date is None:
        return 0.0

    resolved_now = now or datetime.now()
    age_days = max(0, (resolved_now - create_date).days)
    if age_days <= RECENCY_FULL_SCORE_DAYS:
        return RECENCY_SCORE_WEIGHT
    if age_days <= RECENCY_MEDIUM_SCORE_DAYS:
        return 7.0
    if age_days <= RECENCY_LOW_SCORE_DAYS:
        return 4.0
    return 1.0


def calculate_department_score(department_name: str | None) -> float:
    if not department_name:
        return 0.0

    return (
        DEPARTMENT_SCORE_BONUS
        if any(pattern in department_name for pattern in DEPARTMENT_BONUS_PATTERNS)
        else 0.0
    )


def _preview(value: str | None, max_chars: int = 120) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."
