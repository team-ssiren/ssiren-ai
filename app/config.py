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
    openai_model: str = Field(default="gpt-5.5", description="Chat/vision model id")
    llm_temperature: float = Field(default=0.0, description="Used only if llm_send_temperature")
    llm_send_temperature: bool = Field(
        default=False,
        description="GPT-5 family rejects non-default temperature; keep off for those models",
    )
    llm_timeout_seconds: float = Field(default=60.0)
    llm_max_retries: int = Field(default=1)
    llm_max_concurrency: int = Field(default=8, description="Max concurrent LLM calls")

    # --- Embeddings (OpenAI text-embedding-3-small) ---
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536, description="text-embedding-3-small native")
    embedding_max_batch: int = Field(default=128, description="Max texts per request")
    embedding_max_concurrency: int = Field(default=8, description="Max concurrent embedding calls")

    # --- Analyze (① multimodal) guards ---
    analyze_max_images: int = Field(default=5)
    analyze_max_image_mb: int = Field(default=10)

    # --- Domain thresholds (defaults; BE owns final policy) ---
    chatbot_history_max_turns: int = Field(default=10)


@lru_cache
def get_settings() -> Settings:
    """Singleton settings accessor (cached for the process lifetime)."""
    return Settings()
