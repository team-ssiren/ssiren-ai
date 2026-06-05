"""FastAPI application entrypoint.

Phase 0-1: app factory, settings wiring, and the /health endpoint.
Routes and middleware for the AI features are added in later phases.
"""

from fastapi import FastAPI

from app.config import Settings, get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="싸이렌 AI 서버 (internal, BE→AI). Not exposed publicly.",
        docs_url="/docs",
    )

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
