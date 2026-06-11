"""Application configuration loaded from environment / .env.

Settings are validated at startup. Required values (e.g. OPENAI_API_KEY) have no
default, so a missing env var fails fast with a clear error when the app boots.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App meta ---
    app_name: str = "ssairen-ai"
    app_version: str = __version__
    environment: str = Field(default="local", description="local | dev | prod")

    # --- OpenAI (LLM) ---
    openai_api_key: str = Field(..., description="OpenAI API key (required)")
    openai_base_url: str | None = Field(
        default=None, description="OpenAI API base URL override (proxy/Azure/compatible)"
    )
    openai_model: str = Field(
        default="gpt-5.4-mini", description="Chat/vision model id (enrich step)"
    )
    classify_model: str = Field(
        default="gpt-5.4-mini", description="Cheaper model for major/minor classification"
    )
    llm_temperature: float = Field(default=0.0, description="Used only if llm_send_temperature")
    llm_send_temperature: bool = Field(
        default=False,
        description="GPT-5 family rejects non-default temperature; keep off for those models",
    )
    llm_timeout_seconds: float = Field(default=60.0)
    llm_max_retries: int = Field(default=1, description="SDK transport retries (network/5xx/429)")
    structured_output_max_retries: int = Field(
        default=2, description="App-level retries when LLM output fails schema/JSON validation"
    )
    llm_max_concurrency: int = Field(default=8, description="Max concurrent LLM calls")

    # --- Embeddings (OpenAI text-embedding-3-small) ---
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536, description="text-embedding-3-small native")
    embedding_max_batch: int = Field(default=128, description="Max texts per request")
    embedding_max_concurrency: int = Field(default=8, description="Max concurrent embedding calls")

    # --- Analyze (① multimodal) guards ---
    analyze_max_images: int = Field(default=5)
    analyze_max_image_mb: int = Field(default=50, description="Max upload size per image")
    analyze_max_image_pixels: int = Field(
        default=1_000_000, description="Downscale to <= this many pixels before sending to OpenAI"
    )

    # --- Domain thresholds (defaults; BE owns final policy) ---
    chatbot_history_max_turns: int = Field(default=10)
    chatbot_title_max_chars: int = Field(default=10, description="Session title length cap")

    # --- Data.go.kr ---
    data_gokr_api_key: str = Field(default="", description="Public data portal service key")

    # --- SQLite (AI-only: assignment guide + org directory) ---
    sqlite_db_path: str = Field(default="data/ssiren.db", description="AI-only SQLite DB path")
    org_default_region_code: str = Field(
        default="BUNDANG", description="Region key for org resolution (seed scope)"
    )


@lru_cache
def get_settings() -> Settings:
    """Singleton settings accessor (cached for the process lifetime)."""
    return Settings()
