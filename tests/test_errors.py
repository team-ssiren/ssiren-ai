"""Phase 0-2: standard error-response shape and request-id propagation."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.errors import register_exception_handlers  # noqa: E402
from app.api.middleware import REQUEST_ID_HEADER, register_middleware  # noqa: E402
from app.core.errors import LLMError  # noqa: E402


def _app() -> FastAPI:
    app = FastAPI()
    register_middleware(app)
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise LLMError("upstream down")

    @app.get("/unexpected")
    def unexpected():
        raise RuntimeError("kaboom")

    @app.get("/toolarge")
    def toolarge():
        raise HTTPException(status_code=413, detail="image too large")

    @app.get("/guard422")
    def guard422():
        raise HTTPException(status_code=422, detail="too many images")

    return app


client = TestClient(_app(), raise_server_exceptions=False)


def test_app_error_maps_to_standard_json():
    resp = client.get("/boom")
    assert resp.status_code == 502
    body = resp.json()
    assert body["error"]["code"] == "llm_upstream_error"
    assert body["error"]["message"] == "upstream down"
    assert body["error"]["requestId"]
    assert resp.headers[REQUEST_ID_HEADER]


def test_unexpected_error_is_masked():
    resp = client.get("/unexpected")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Internal server error"


def test_request_id_is_echoed():
    resp = client.get("/boom", headers={REQUEST_ID_HEADER: "fixed-rid-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "fixed-rid-123"
    assert resp.json()["error"]["requestId"] == "fixed-rid-123"


def test_http_exception_uses_standard_envelope():
    resp = client.get("/toolarge")
    assert resp.status_code == 413
    body = resp.json()
    assert "detail" not in body  # not FastAPI's default shape
    assert body["error"]["code"] == "payload_too_large"
    assert body["error"]["message"] == "image too large"
    assert body["error"]["requestId"]


def test_guard_422_maps_to_validation_error():
    body = client.get("/guard422").json()
    assert body["error"]["code"] == "validation_error"
