"""Phase 0-2: structured-output helper behavior with a faked OpenAI client."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.core import structured  # noqa: E402
from app.core.errors import LLMError, LLMRefusalError  # noqa: E402


class _Schema(BaseModel):
    label: str
    score: int


def _fake_client(*, parsed=None, refusal=None):
    class _Message:
        def __init__(self):
            self.parsed = parsed
            self.refusal = refusal

    class _Choice:
        message = _Message()

    class _Completion:
        choices = [_Choice()]

    class _Completions:
        async def parse(self, **kwargs):
            return _Completion()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    return _Client()


@pytest.mark.anyio
async def test_returns_parsed_object(monkeypatch):
    expected = _Schema(label="ROAD_DAMAGE", score=4)
    monkeypatch.setattr(structured, "get_openai_client", lambda: _fake_client(parsed=expected))

    result = await structured.complete_structured(messages=[], schema=_Schema)
    assert result == expected


@pytest.mark.anyio
async def test_refusal_raises(monkeypatch):
    monkeypatch.setattr(
        structured, "get_openai_client", lambda: _fake_client(refusal="cannot comply")
    )
    with pytest.raises(LLMRefusalError):
        await structured.complete_structured(messages=[], schema=_Schema)


@pytest.mark.anyio
async def test_empty_output_raises(monkeypatch):
    monkeypatch.setattr(structured, "get_openai_client", lambda: _fake_client(parsed=None))
    with pytest.raises(LLMError):
        await structured.complete_structured(messages=[], schema=_Schema)


@pytest.fixture
def anyio_backend():
    return "asyncio"
