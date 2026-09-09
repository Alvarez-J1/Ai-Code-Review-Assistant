from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Code Review Assistant"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", validation_alias="OPENAI_MODEL")
    openai_timeout_seconds: float = Field(default=30.0, validation_alias="OPENAI_TIMEOUT_SECONDS")
    openai_max_output_tokens: int = Field(default=2_000, validation_alias="OPENAI_MAX_OUTPUT_TOKENS")
    github_token: SecretStr | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    github_api_base_url: str = Field(default="https://api.github.com", validation_alias="GITHUB_API_BASE_URL")
    github_api_version: str = Field(default="2026-03-10", validation_alias="GITHUB_API_VERSION")
    github_timeout_seconds: float = Field(default=20.0, validation_alias="GITHUB_TIMEOUT_SECONDS")
    github_max_files: int = Field(default=3_000, validation_alias="GITHUB_MAX_FILES")
    cors_allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ai_code_review",
        validation_alias="DATABASE_URL",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @computed_field
    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
