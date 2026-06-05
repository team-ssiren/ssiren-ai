"""FastAPI application entrypoint.

App factory wiring settings, request-context middleware, standard error handlers,
and the /health endpoint. Feature routes are mounted in later phases.
"""

import logging

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.middleware import register_middleware
from app.config import Settings, get_settings


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )


def create_app() -> FastAPI:
    _configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="싸이렌 AI 서버 (internal, BE→AI). Not exposed publicly.",
        docs_url="/docs",
    )

    register_middleware(app)
    register_exception_handlers(app)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        s: Settings = get_settings()
        return {
            "status": "ok",
            "app": s.app_name,
            "version": s.app_version,
            "environment": s.environment,
            "models": {
                "llm": s.openai_model,
                "embedding": s.embedding_model,
                "embedding_device": s.embedding_device,
                "embedding_dimension": s.embedding_dimension,
            },
        }

    return app


app = create_app()
