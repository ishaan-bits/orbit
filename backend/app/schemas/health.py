from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Overall service status: ok or degraded")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    environment: str = Field(description="Runtime environment")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    checks: dict[str, str] = Field(description="Status of individual dependencies")
