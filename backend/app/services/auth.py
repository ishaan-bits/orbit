"""Accounts, default role seeding and role-based access-control queries."""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.auth import DocumentPermission, Role, User
from app.models.knowledge import Document, Folder, folder_roles
from app.services.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRoleError,
)

logger = logging.getLogger("orbit.services.auth")

DEFAULT_ROLES = {
    "Admin": "Full access to every folder, document and conversation",
    "HR": "Access to folders shared with the HR role",
    "Engineering": "Access to folders shared with the Engineering role",
}
REGISTERABLE_ROLES = ("HR", "Engineering")
DEFAULT_ROLE = "Engineering"
ADMIN_ROLE = "Admin"
GENERAL_FOLDER_NAME = "General"


def ensure_rbac_seed(db: Session) -> None:
    """Idempotently create the default roles and the shared General folder."""
    for name, description in DEFAULT_ROLES.items():
        existing = db.scalar(select(Role).where(Role.name == name))
        if existing is None:
            db.add(Role(name=name, description=description))

    general = db.scalar(select(Folder).where(Folder.name == GENERAL_FOLDER_NAME))
    if general is None:
        general = Folder(name=GENERAL_FOLDER_NAME)
        db.add(general)
        db.flush()

    role_rows = list(db.scalars(select(Role)).all())
    allowed = {role.name for role in general.allowed_roles}
    for role in role_rows:
        if role.name not in allowed:
            general.allowed_roles.append(role)

    db.commit()
    logger.info("rbac.seeded", extra={"roles": list(DEFAULT_ROLES)})


def get_role(db: Session, name: str) -> Optional[Role]:
    return db.scalar(select(Role).where(Role.name == name))


def get_roles_by_names(db: Session, names: list[str]) -> list[Role]:
    """Resolve role names, raising ``InvalidRoleError`` for unknown ones."""
    rows = db.scalars(select(Role).where(Role.name.in_(names))).all()
    found = {row.name: row for row in rows}
    missing = [name for name in names if name not in found]
    if missing:
        raise InvalidRoleError(f"Unknown role: {', '.join(missing)}")
    # preserve caller order
    return [found[name] for name in names]


def register_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role_name: Optional[str] = None,
) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user_count = int(db.scalar(select(func.count()).select_from(User)) or 0)
    if user_count == 0:
        # the first account bootstraps the platform as Admin
        resolved_name = ADMIN_ROLE
    else:
        resolved_name = role_name or DEFAULT_ROLE
        if resolved_name == ADMIN_ROLE or resolved_name not in REGISTERABLE_ROLES:
            raise InvalidRoleError(
                f"Role '{resolved_name}' is not available for registration"
            )

    role = get_role(db, resolved_name)
    if role is None:
        raise InvalidRoleError(f"Role '{resolved_name}' has not been seeded")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(
        "auth.registered",
        extra={"user_id": user.id, "email": user.email, "role": role.name},
    )
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise InvalidCredentialsError()
    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    return user


def is_admin(user: User) -> bool:
    return user.role.name == ADMIN_ROLE


def get_general_folder(db: Session) -> Optional[Folder]:
    return db.scalar(select(Folder).where(Folder.name == GENERAL_FOLDER_NAME))


def can_access_folder(user: User, folder: Folder) -> bool:
    if is_admin(user):
        return True
    return any(role.id == user.role_id for role in folder.allowed_roles)


def can_access_document(db: Session, user: User, document: Document) -> bool:
    if is_admin(user):
        return True
    if document.folder is not None and can_access_folder(user, document.folder):
        return True
    grant = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.role_id == user.role_id,
        )
    )
    return grant is not None


def get_accessible_folders(db: Session, user: User) -> list[Folder]:
    statement = select(Folder)
    if not is_admin(user):
        statement = statement.join(
            folder_roles, folder_roles.c.folder_id == Folder.id
        ).where(folder_roles.c.role_id == user.role_id)
    return list(db.scalars(statement.order_by(Folder.name)).all())


def get_accessible_document_ids(db: Session, user: User) -> Optional[set[str]]:
    """Document ids the user may read; ``None`` means unrestricted (Admin)."""
    if is_admin(user):
        return None

    folder_docs = (
        select(Document.id)
        .join(Folder, Document.folder_id == Folder.id)
        .join(folder_roles, folder_roles.c.folder_id == Folder.id)
        .where(
            folder_roles.c.role_id == user.role_id,
            Document.deleted_at.is_(None),
        )
    )
    permitted = select(DocumentPermission.document_id).where(
        DocumentPermission.role_id == user.role_id
    )
    rows = set(db.scalars(folder_docs).all())
    rows.update(db.scalars(permitted).all())
    return rows
