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


def _fake_client(*, parsed=None, refusal=None, raises=None):
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
            if raises is not None:
                raise raises
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


@pytest.mark.anyio
async def test_schema_validation_error_becomes_llm_error(monkeypatch):
    # 재시도 소진 후에도 부적합하면 → 502 LLMError 로 분류 + 시도마다 메트릭 기록.
    import json as _json

    from app.config import get_settings
    from app.core import metrics

    monkeypatch.setattr(get_settings(), "structured_output_max_retries", 1)  # 총 2회 시도

    try:
        _Schema.model_validate({"label": "x"})  # missing 'score' → ValidationError
    except Exception as ve:  # noqa: BLE001
        verr = ve

    for raised in (verr, _json.JSONDecodeError("bad", "doc", 0)):
        monkeypatch.setattr(
            structured, "get_openai_client", lambda r=raised: _fake_client(raises=r)
        )
        before = metrics.snapshot()["llm_errors"]
        with pytest.raises(LLMError):
            await structured.complete_structured(messages=[], schema=_Schema)
        assert metrics.snapshot()["llm_errors"] == before + 2  # 2회 시도 모두 오류 기록


@pytest.mark.anyio
async def test_retries_then_succeeds(monkeypatch):
    # 첫 시도는 스키마 불일치, 두 번째 시도는 성공 → 재시도로 복구.
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "structured_output_max_retries", 2)
    expected = _Schema(label="ROAD_DAMAGE", score=4)

    try:
        _Schema.model_validate({})  # ValidationError
    except Exception as ve:  # noqa: BLE001
        verr = ve

    calls = {"n": 0}

    class _Completions:
        async def parse(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise verr

            class _Msg:
                parsed = expected
                refusal = None

            class _Choice:
                message = _Msg()

            class _Completion:
                choices = [_Choice()]

            return _Completion()

    class _Client:
        class chat:
            completions = _Completions()

    monkeypatch.setattr(structured, "get_openai_client", lambda: _Client())
    result = await structured.complete_structured(messages=[], schema=_Schema)
    assert result == expected
    assert calls["n"] == 2  # 1회 실패 후 재시도로 성공


@pytest.fixture
def anyio_backend():
    return "asyncio"
