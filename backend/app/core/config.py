import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
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
    database_url: str = "sqlite:///./data/orbit.db"
    chroma_path: str = "./chroma_db"
    # absolute path; empty -> `uploads/` next to the `app` package
    uploads_dir: str = ""
    redis_url: str = "redis://redis:6379"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440
    cookie_secure: bool = False

    # seed the NovaTech demo tenant (folders + accounts) on startup
    seed_demo: bool = False

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
