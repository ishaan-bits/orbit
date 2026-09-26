"""Shared FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

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
