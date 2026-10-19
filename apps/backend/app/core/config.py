"""Application configuration and environment settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loads and validates environment settings for the Mound platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
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


settings = Settings()
