from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Overall service status: ok or degraded")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    environment: str = Field(description="Runtime environment")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    checks: dict[str, str] = Field(description="Status of individual dependencies")
    rss_mb: Optional[int] = Field(
        default=None, description="Process resident memory in MB"
    )
    embedding_provider: Optional[str] = Field(
        default=None, description="Active embedding provider (local or gemini)"
    )
    gemini_key_configured: Optional[bool] = Field(
        default=None, description="Whether GEMINI_API_KEY is set (never the key)"
    )
    local_model_loaded: Optional[bool] = Field(
        default=None, description="Whether the SentenceTransformer model is in memory"
    )
