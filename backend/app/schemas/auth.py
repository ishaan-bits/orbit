"""Authentication request/response schemas."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are always stored in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, description="Email address")
    password: str = Field(min_length=8, max_length=72, description="Password")
    full_name: Optional[str] = Field(
        default=None, max_length=100, description="Display name"
    )
    role: Optional[str] = Field(
        default=None, description="Requested role (HR or Engineering)"
    )

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        import re

        cleaned = value.strip().lower()
        if not re.match(EMAIL_PATTERN, cleaned):
            raise ValueError("Invalid email address")
        return cleaned


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, description="Email address")
    password: str = Field(min_length=1, max_length=72, description="Password")

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="User identifier")
    email: str = Field(description="Email address")
    full_name: Optional[str] = Field(default=None, description="Display name")
    role: str = Field(description="Assigned role name")
    is_active: bool = Field(description="Whether the account is active")
    created_at: datetime = Field(description="Registration timestamp (UTC)")

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc(value)
