"""Per-document role grants."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import DocumentPermission, Role
from app.models.knowledge import Document
from app.services.errors import DocumentNotFoundError, InvalidRoleError

logger = logging.getLogger("orbit.services.permissions")


def grant_permission(
    db: Session, document_id: str, role_name: str
) -> DocumentPermission:
    document = db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError(document_id)

    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise InvalidRoleError(f"Unknown role: {role_name}")

    existing = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.role_id == role.id,
        )
    )
    if existing is not None:
        return existing

    permission = DocumentPermission(document_id=document.id, role_id=role.id)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    logger.info(
        "permissions.granted",
        extra={
            "document_id": document.id,
            "role": role.name,
            "permission_id": permission.id,
        },
    )
    return permission


def revoke_permission(db: Session, document_id: str, role_name: str) -> bool:
    document = db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError(document_id)

    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise InvalidRoleError(f"Unknown role: {role_name}")

    permission = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.role_id == role.id,
        )
    )
    if permission is None:
        return False

    db.delete(permission)
    db.commit()
    logger.info(
        "permissions.revoked",
        extra={"document_id": document.id, "role": role.name},
    )
    return True
