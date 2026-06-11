"""Structured-output helper.

Wraps OpenAI Structured Outputs (``chat.completions.parse``) so callers get a
validated Pydantic object back — enum violations, missing fields, and free-text
drift are rejected at the schema layer. Transient *transport* failures are retried
by the SDK; *non-conforming output* (schema/JSON validation failure or empty parse)
is retried app-side up to ``structured_output_max_retries``. Remaining failures
surface as ``LLMError``; a deliberate model refusal surfaces as ``LLMRefusalError``.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAIError
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.core import metrics
from app.core.concurrency import llm_slot
from app.core.errors import LLMError, LLMRefusalError
from app.core.llm import get_openai_client

logger = logging.getLogger("ssairen.llm")

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

    # Transport failures (network/5xx/429/timeout) are retried by the SDK. Output that
    # doesn't conform to the (possibly dynamic enum) schema is non-deterministic, so we
    # retry the whole call app-side up to ``structured_output_max_retries`` times.
    attempts = 1 + max(0, settings.structured_output_max_retries)
    last_reason = "unknown"
    for attempt in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            async with llm_slot():
                completion = await client.chat.completions.parse(**params)
        except OpenAIError as exc:  # network, 5xx, rate limit, timeout, length/content-filter
            metrics.record_llm(
                prompt_tokens=0, completion_tokens=0,
                latency_ms=(time.perf_counter() - start) * 1000, error=True,
            )
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        except (ValidationError, json.JSONDecodeError) as exc:
            # JSON doesn't satisfy the schema (or isn't JSON) — retryable.
            metrics.record_llm(
                prompt_tokens=0, completion_tokens=0,
                latency_ms=(time.perf_counter() - start) * 1000, error=True,
            )
            last_reason = f"schema_mismatch:{exc.__class__.__name__}"
            logger.warning("structured output invalid (attempt %d/%d): %s",
                           attempt, attempts, exc.__class__.__name__)
            continue

        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(completion, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        message = completion.choices[0].message

        if getattr(message, "refusal", None):  # deliberate model decision — not retried
            metrics.record_llm(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
            raise LLMRefusalError(message.refusal)

        parsed = getattr(message, "parsed", None)
        if parsed is None:  # empty/non-conforming output — retryable
            metrics.record_llm(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                latency_ms=latency_ms, error=True,
            )
            last_reason = "empty_structured_output"
            logger.warning("empty structured output (attempt %d/%d)", attempt, attempts)
            continue

        metrics.record_llm(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, latency_ms=latency_ms,
        )
        logger.info(
            "llm_call model=%s latency_ms=%.0f prompt_tokens=%s completion_tokens=%s attempt=%d/%d",
            params["model"], latency_ms, prompt_tokens, completion_tokens, attempt, attempts,
        )
        return parsed

    raise LLMError(f"LLM structured output failed after {attempts} attempts ({last_reason})")
