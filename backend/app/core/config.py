from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_env: str = "development"
    app_name: str = "InstaPilot AI"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    jwt_secret_key: str = "change-me-in-production-min-32-chars"
    token_encryption_key: str = "change-me-fernet-or-32-byte-base64-key"

    database_url: str = "postgresql+asyncpg://instapilot:instapilot_dev_pass@localhost:5432/instapilot"
    redis_url: str = "redis://localhost:6379/0"

    default_llm_provider: str = "gemini"
    default_llm_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    groq_api_key: str = ""

    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_verify_token: str = ""
    meta_redirect_uri: str = "http://localhost:8000/api/v1/instagram/oauth/callback"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
