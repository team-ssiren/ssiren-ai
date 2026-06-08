"""FastAPI application entrypoint.

App factory wiring settings, request-context middleware, standard error handlers,
and the /health endpoint. Feature routes are mounted in later phases.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.middleware import register_middleware
from app.api.routes import chatbot, embeddings, reports
from app.config import Settings, get_settings
from app.core import metrics
from app.core.concurrency import init_semaphores

logger = logging.getLogger("ssairen.startup")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_semaphores(settings.llm_max_concurrency, settings.embedding_max_concurrency)
    logger.info(
        "concurrency limits: llm=%d embedding=%d",
        settings.llm_max_concurrency,
        settings.embedding_max_concurrency,
    )
    yield


def create_app() -> FastAPI:
    _configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="싸이렌 AI 서버 (internal, BE→AI). Not exposed publicly.",
        docs_url="/docs",
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(embeddings.router)
    app.include_router(reports.router)
    app.include_router(chatbot.router)

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
                "embedding_dimension": s.embedding_dimension,
            },
        }

    @app.get("/metrics", tags=["meta"])
    def metrics_endpoint() -> dict:
        return metrics.snapshot()

    return app


app = create_app()
