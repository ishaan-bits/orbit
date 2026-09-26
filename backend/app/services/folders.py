import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth import Role
from app.models.knowledge import Document, Folder
from app.services.errors import FolderAlreadyExistsError

logger = logging.getLogger("orbit.services.folders")


def list_folders(db: Session) -> list[tuple[Folder, int]]:
    """Return every folder with its active document count."""
    statement = (
        select(Folder, func.count(Document.id).label("document_count"))
        .outerjoin(
            Document,
            (Document.folder_id == Folder.id) & (Document.deleted_at.is_(None)),
        )
        .group_by(Folder.id)
        .order_by(Folder.name)
    )
    return [(row[0], int(row[1])) for row in db.execute(statement).all()]


def create_folder(
    db: Session,
    name: str,
    allowed_roles: Optional[list[Role]] = None,
) -> Folder:
    cleaned = name.strip()
    existing = db.scalar(
        select(Folder).where(func.lower(Folder.name) == cleaned.lower()),
    )
    if existing is not None:
        raise FolderAlreadyExistsError(cleaned)

    folder = Folder(name=cleaned)
    if allowed_roles is None:
        # unrestricted by default: every seeded role gets access
        folder.allowed_roles = list(db.scalars(select(Role)).all())
    else:
        folder.allowed_roles = list(allowed_roles)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    logger.info(
        "folders.created",
        extra={
            "folder_id": folder.id,
            "folder_name": folder.name,
            "allowed_roles": [role.name for role in folder.allowed_roles],
        },
    )
    return folder
