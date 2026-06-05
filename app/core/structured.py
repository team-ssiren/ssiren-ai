"""Structured-output helper.

Wraps OpenAI Structured Outputs (``chat.completions.parse``) so callers get a
validated Pydantic object back — enum violations, missing fields, and free-text
drift are rejected at the schema layer. Transient upstream failures are retried by
the SDK (configured on the client); remaining failures surface as ``LLMError``.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAIError
from pydantic import BaseModel

from app.config import get_settings
from app.core.errors import LLMError, LLMRefusalError
from app.core.llm import get_openai_client

# OpenAI chat message list (role/content dicts, possibly with image parts).
Messages = list[dict[str, Any]]


async def complete_structured[T: BaseModel](
    *,
    messages: Messages,
    schema: type[T],
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> T:
    """Call the LLM and return a validated instance of ``schema``.

    Raises:
        LLMRefusalError: the model declined to answer.
        LLMError: upstream failure or empty/invalid structured output.
    """
    settings = get_settings()
    client = get_openai_client()

    # Build params conditionally — omit optionals entirely when unset, since some
    # models reject explicit nulls (e.g. max_tokens) or non-default temperature.
    params: dict[str, Any] = {
        "model": model or settings.openai_model,
        "messages": messages,
        "response_format": schema,
    }
    # Some models (GPT-5 family) only accept the default temperature; gate sending it.
    if settings.llm_send_temperature:
        temp = settings.llm_temperature if temperature is None else temperature
        if temp is not None:
            params["temperature"] = temp
    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    try:
        completion = await client.chat.completions.parse(**params)
    except OpenAIError as exc:  # network, 5xx, rate limit, timeout (post-retry)
        raise LLMError(f"OpenAI request failed: {exc}") from exc

    message = completion.choices[0].message

    if getattr(message, "refusal", None):
        raise LLMRefusalError(message.refusal)

    parsed = getattr(message, "parsed", None)
    if parsed is None:
        raise LLMError("LLM returned empty structured output")

    return parsed
