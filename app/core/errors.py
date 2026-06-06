"""Domain exception types.

Each carries a stable machine-readable ``code`` and an HTTP status. The API layer
(``app/api/errors.py``) turns these into a standard error JSON response.
"""

from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.__doc__ or "error"
        super().__init__(self.message)


class LLMError(AppError):
    """Upstream LLM call failed."""

    code = "llm_upstream_error"
    http_status = 502


class LLMRefusalError(AppError):
    """LLM refused to produce a structured answer."""

    code = "llm_refusal"
    http_status = 422


class EmbeddingError(AppError):
    """Embedding computation failed."""

    code = "embedding_error"
    http_status = 500
