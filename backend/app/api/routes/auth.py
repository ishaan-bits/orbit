"""Auth endpoints: register, login, me, logout (JWT in HTTP-only cookie)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import SESSION_COOKIE, create_access_token
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services import auth as auth_service
from app.services.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRoleError,
)

router = APIRouter(tags=["auth"])
logger = logging.getLogger("orbit.api.auth")


def _set_session_cookie(response: Response, token: str) -> None:
    """Set the cross-origin session cookie (Vercel page + Render API).

    Fixed production contract: `SameSite=None; Secure` is required for the
    browser to store a cross-site cookie at all (Safari rejects the rest),
    no Domain attribute keeps it host-only, and max-age matches the7-day
    session window.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=604800,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="none",
        secure=True,
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _issue_session(response: Response, user: User) -> UserResponse:
    token = create_access_token(user.id, user.role.name)
    _set_session_cookie(response, token)
    return _user_response(user)


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create an account. The first account is always the Admin."""
    try:
        user = auth_service.register_user(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role_name=payload.role,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    except InvalidRoleError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from None
    return _issue_session(response, user)


@router.post("/auth/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Verify credentials and start a session cookie."""
    try:
        user = auth_service.authenticate(db, payload.email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from None
    return _issue_session(response, user)


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user."""
    return _user_response(user)


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    """Clear the session cookie."""
    _clear_session_cookie(response)
    return {"message": "Logged out"}
