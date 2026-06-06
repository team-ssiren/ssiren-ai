"""Request-context middleware: assign a request id and emit an access log line."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

logger = logging.getLogger("ssairen.access")

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s (%.1fms) rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
