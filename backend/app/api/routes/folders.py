import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.schemas.knowledge import FolderCreate, FolderResponse
from app.services import auth as auth_service
from app.services import folders as folders_service
from app.services.errors import (
    FolderAccessDeniedError,
    FolderAlreadyExistsError,
    InvalidRoleError,
)

router = APIRouter(tags=["folders"])
logger = logging.getLogger("orbit.api.folders")


def _folder_response(folder, document_count: int) -> FolderResponse:
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        document_count=document_count,
        allowed_roles=[role.name for role in folder.allowed_roles],
        created_at=folder.created_at,
    )


@router.get("/folders", response_model=list[FolderResponse])
def list_folders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FolderResponse]:
    """List folders the caller's role may access, with document counts."""
    return [
        _folder_response(folder, count)
        for folder, count in folders_service.list_folders(db)
        if auth_service.can_access_folder(user, folder)
    ]


@router.post(
    "/folders",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_folder(
    payload: FolderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FolderResponse:
    """Create a folder. Names are unique (case-insensitive)."""
    allowed_roles = None
    if payload.allowed_roles is not None:
        try:
            allowed_roles = auth_service.get_roles_by_names(db, payload.allowed_roles)
        except InvalidRoleError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
            ) from None
        if not any(role.id == user.role_id for role in allowed_roles):
            allowed_roles.append(user.role)
    try:
        folder = folders_service.create_folder(db, payload.name, allowed_roles)
    except FolderAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A folder named '{payload.name.strip()}' already exists",
        ) from None
    except FolderAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(error)
        ) from None
    return _folder_response(folder, 0)
