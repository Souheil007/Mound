"""Application configuration and environment settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILES = (
    _BACKEND_DIR / ".env",
    Path(".env"),
)


class Settings(BaseSettings):
    """Loads and validates environment settings for the Mound platform."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_port: int = 8000
    debug: bool = True

    # Database & Cache
    database_url: str = "postgresql+asyncpg://mound_user:mound_password@localhost:5432/mound_db"
    redis_url: str = "redis://localhost:6379/0"

    # Embedding Model (sentence-transformers/all-MiniLM-L6-v2)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # Rate Limiting
    rate_limit_enabled: bool = True

    # Linter
    evidence_url_verification_enabled: bool = True

    # Authentication & Security
    jwt_secret_key: str = "mound_insecure_jwt_dev_secret_key_change_in_production_32b"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    google_client_id: str = ""

    # Autonomous Scout Swarm & External Adapters
    scout_cron_interval_minutes: int = 120
    github_token: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_target_subreddits: list[str] | None = None

    # Tier-2 LLM Evaluator
    llm_provider: str = "mistral"  # "mistral", "gemini", "openai", "anthropic", "ollama", or "semantic_embedding"
    gemini_api_key: str | None = None
    mistral_api_key: str | None = None
    mistral_model: str = "open-mistral-7b"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"


settings = Settings()
