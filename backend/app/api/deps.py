"""Shared FastAPI dependencies for authentication."""

import hmac
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import SESSION_COOKIE, decode_access_token
from app.db.session import get_db
from app.models.auth import User

_UNAUTHENTICATED_HEADERS = {"WWW-Authenticate": "Bearer"}


def _unauthenticated(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_UNAUTHENTICATED_HEADERS,
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the authenticated user from the HTTP-only session cookie.

    An ``Authorization: Bearer`` header is accepted as a fallback for
    non-browser clients.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
    if not token:
        raise _unauthenticated("Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise _unauthenticated("Session is invalid or has expired")

    user = db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise _unauthenticated("Session is invalid or has expired")
    return user


def get_retry_caller(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Resolve the caller of ``POST /documents/retry-pending``.

    The Render cron job authenticates with ``Authorization: Bearer
    <CRON_SECRET>`` and is treated as the system caller (returns ``None``,
    so the retry covers every pending document). Any other request must
    carry a valid session like the rest of the API.
    """
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if settings.cron_secret and hmac.compare_digest(token, settings.cron_secret):
            return None
    return get_current_user(request, db)
