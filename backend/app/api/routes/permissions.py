"""Per-document permission management (Admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.schemas.knowledge import (
    DocumentPermissionCreate,
    DocumentPermissionResponse,
)
from app.services import auth as auth_service
from app.services import permissions as permissions_service
from app.services.errors import (
    DocumentNotFoundError,
    InvalidRoleError,
)

router = APIRouter(tags=["permissions"])


def _require_admin(user: User) -> None:
    if not auth_service.is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can manage document permissions",
        )


@router.post(
    "/permissions",
    response_model=DocumentPermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_permission(
    payload: DocumentPermissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentPermissionResponse:
    """Grant a role view access to a specific document."""
    _require_admin(user)
    try:
        permission = permissions_service.grant_permission(
            db, payload.document_id, payload.role
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{payload.document_id}' was not found",
        ) from None
    except InvalidRoleError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from None
    return DocumentPermissionResponse(
        id=permission.id,
        document_id=permission.document_id,
        role=permission.role.name,
        created_at=permission.created_at,
    )


@router.delete("/permissions")
def delete_permission(
    payload: DocumentPermissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Revoke a role's access to a specific document."""
    _require_admin(user)
    try:
        revoked = permissions_service.revoke_permission(
            db, payload.document_id, payload.role
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{payload.document_id}' was not found",
        ) from None
    except InvalidRoleError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from None
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{payload.role}' does not have access to this document",
        )
    return {"status": "revoked"}
