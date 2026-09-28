import json
from functools import lru_cache
from typing import Any, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    app_name: str = "Orbit"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    # "local" (SentenceTransformers) or "gemini" (API, low-RAM Render).
    embedding_provider: str = "local"
    # What to do when the gemini embedder fails: "local" loads the
    # SentenceTransformer model (dev only), "none" propagates the failure so
    # indexing records a clean index_error. Ignored in production, where the
    # fallback would OOM the 512MB instance and is never allowed.
    embedding_fallback: str = "local"
    database_url: str = "sqlite:///./data/orbit.db"
    chroma_path: str = "./chroma_db"
    # absolute path; empty -> `uploads/` next to the `app` package
    uploads_dir: str = ""
    redis_url: str = "redis://redis:6379"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440
    cookie_secure: bool = False

    # NovaTech demo tenant (folders + accounts):
    #   true  -> always seed (idempotent)
    #   false -> never seed
    #   unset -> seed only on first run (empty users table)
    seed_demo: Optional[bool] = None

    cors_origins: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: Any) -> Any:
        """Accept a JSON list or a comma-separated string of origins."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return [part.strip() for part in text.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def _production_storage_defaults(self) -> "Settings":
        """Default to the Render persistent-disk paths in production.

        When ENVIRONMENT=production and a storage setting was not provided
        (still at its local default), point it at the mounted disk at
        `/var/data`. Local development keeps the existing relative paths.
        """
        if self.environment == "production":
            fields = type(self).model_fields
            if self.database_url == fields["database_url"].default:
                self.database_url = "sqlite:////var/data/orbit.db"
            if self.chroma_path == fields["chroma_path"].default:
                self.chroma_path = "/var/data/chroma"
            if not self.uploads_dir.strip():
                self.uploads_dir = "/var/data/uploads"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
