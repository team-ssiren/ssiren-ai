"""OpenAI client wrapper.

A single cached AsyncOpenAI client configured with timeout and retry from settings.
The SDK retries transient failures up to ``llm_max_retries`` times internally.
"""

from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    s = get_settings()
    kwargs: dict = {
        "api_key": s.openai_api_key,
        "timeout": s.llm_timeout_seconds,
        "max_retries": s.llm_max_retries,
    }
    if s.openai_base_url:  # omit when unset so the SDK uses its default endpoint
        kwargs["base_url"] = s.openai_base_url
    return AsyncOpenAI(**kwargs)
