"""Password hashing and JWT session tokens (HS256, HTTP-only cookie)."""

import time
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import settings

SESSION_COOKIE = "orbit_session"
ALGORITHM = "HS256"


def _secret() -> str:
    return settings.jwt_secret or "orbit-development-secret-change-me-1234"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, role_name: str) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role_name,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Return the token payload, or ``None`` when the token is invalid/expired."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
