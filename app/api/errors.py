"""Standard error responses.

Maps domain ``AppError``s (and uncaught exceptions) to a consistent JSON shape:

    {"error": {"code": "...", "message": "...", "requestId": "..."}}
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import get_request_id
from app.core.errors import AppError

logger = logging.getLogger("ssairen.api")

# Map HTTP status -> stable machine-readable code for the error envelope.
_HTTP_ERROR_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
}


class ErrorDetail(BaseModel):
    code: str
    message: str
    requestId: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _payload(code: str, message: str, request: Request) -> dict:
    return ErrorResponse(
        error=ErrorDetail(code=code, message=message, requestId=get_request_id(request))
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error code=%s status=%s msg=%s", exc.code, exc.http_status, exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content=_payload(exc.code, exc.message, request),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_payload("validation_error", str(exc.errors()), request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Route-level guards raise HTTPException; normalize to the standard envelope.
        code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code, str(exc.detail), request),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_payload("internal_error", "Internal server error", request),
        )
