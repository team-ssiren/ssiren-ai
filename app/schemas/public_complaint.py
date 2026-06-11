"""Public complaint similar-case API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PublicComplaintApiItem(BaseModel):
    """External item shape from Data.go.kr, kept close to source field names."""

    title: str | None = None
    content: str | None = None
    create_date: str | None = None
    main_sub_name: str | None = None
    dep_name: str | None = None


class PublicComplaintApiResponse(BaseModel):
    """Normalized external response wrapper.

    The public API can wrap items differently by gateway/version, so parsing is
    defensive and extracts dictionaries that contain at least one expected field.
    """

    items: list[PublicComplaintApiItem] = Field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Any) -> PublicComplaintApiResponse:
        return cls(
            items=[PublicComplaintApiItem.model_validate(item) for item in _iter_items(payload)]
        )


class SimilarComplaintCase(BaseModel):
    """Internal DTO used by the future RAG pipeline."""

    title: str
    content: str
    createDate: datetime | None
    mainSubName: str | None
    departmentName: str | None
    embeddingText: str

    @classmethod
    def from_api_item(cls, item: PublicComplaintApiItem) -> SimilarComplaintCase | None:
        title = _clean(item.title)
        content = _clean(item.content)
        if not title and not content:
            return None

        return cls(
            title=title,
            content=content,
            createDate=_parse_create_date(item.create_date),
            mainSubName=_optional_clean(item.main_sub_name),
            departmentName=_optional_clean(item.dep_name),
            embeddingText=_build_embedding_text(title, content),
        )


class RankedSimilarComplaintCase(BaseModel):
    """Similar complaint case ranked by embedding similarity."""

    title: str
    content: str
    createDate: datetime | None
    mainSubName: str | None
    departmentName: str | None
    embeddingScore: float

    @classmethod
    def from_case(
        cls,
        case: SimilarComplaintCase,
        embedding_score: float,
    ) -> RankedSimilarComplaintCase:
        return cls(
            title=case.title,
            content=case.content,
            createDate=case.createDate,
            mainSubName=case.mainSubName,
            departmentName=case.departmentName,
            embeddingScore=embedding_score,
        )


_EXPECTED_FIELDS = {"title", "content", "create_date", "main_sub_name", "dep_name"}


def _iter_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if _EXPECTED_FIELDS.intersection(value.keys()):
            return [value]

        items: list[dict[str, Any]] = []
        for child in value.values():
            items.extend(_iter_items(child))
        return items

    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for child in value:
            items.extend(_iter_items(child))
        return items

    return []


def _clean(value: str | None) -> str:
    return value.strip() if value else ""


def _optional_clean(value: str | None) -> str | None:
    cleaned = _clean(value)
    return cleaned or None


def _build_embedding_text(title: str, content: str) -> str:
    return "\n".join(part for part in (title, content) if part)


def _parse_create_date(value: str | None) -> datetime | None:
    cleaned = _clean(value)
    if not cleaned:
        return None

    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None
