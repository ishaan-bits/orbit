"""First-launch demo seed: the NovaTech Systems sample tenant.

Idempotent — safe to run on every startup. Creates the demo company folders
and demo accounts exactly once, and never touches existing rows.
"""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth import Role, User
from app.models.knowledge import Folder
from app.services.auth import ensure_rbac_seed

logger = logging.getLogger("orbit.services.demo_seed")

DEMO_COMPANY = "NovaTech Systems"
DEMO_PASSWORD = "Orbit123"

# folder name -> roles allowed to see it (Admin always sees everything)
DEMO_FOLDERS: dict[str, list[str]] = {
    "HR": ["HR"],
    "Engineering": ["Engineering"],
    "Product": ["Engineering"],
    "Security": ["Engineering"],
    "Legal": ["HR"],
}

# (email, role, full name)
DEMO_USERS: list[tuple[str, str, str]] = [
    ("admin@novatech.com", "Admin", "Avery Chen"),
    ("hr@novatech.com", "HR", "Jordan Lee"),
    ("eng@novatech.com", "Engineering", "Sam Rivera"),
]


def ensure_demo_seed(db: Session) -> dict[str, list[str]]:
    """Create demo folders and users if missing. Returns what was created."""
    ensure_rbac_seed(db)  # roles + the shared General folder

    roles = {role.name: role for role in db.scalars(select(Role)).all()}
    created: dict[str, list[str]] = {"folders": [], "users": []}

    for folder_name, allowed in DEMO_FOLDERS.items():
        existing = db.scalar(
            select(Folder).where(func.lower(Folder.name) == folder_name.lower())
        )
        if existing is not None:
            continue
        folder = Folder(
            name=folder_name,
            allowed_roles=[roles[name] for name in allowed if name in roles],
        )
        db.add(folder)
        created["folders"].append(folder_name)

    for email, role_name, full_name in DEMO_USERS:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            continue
        role: Optional[Role] = roles.get(role_name)
        if role is None:
            logger.warning("demo_seed.unknown_role", extra={"role": role_name})
            continue
        db.add(
            User(
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=full_name,
                role_id=role.id,
            )
        )
        created["users"].append(email)

    db.commit()

    if created["folders"] or created["users"]:
        logger.info(
            "demo_seed.completed",
            extra={
                "company": DEMO_COMPANY,
                "folders": created["folders"],
                "users": created["users"],
            },
        )
    else:
        logger.info("demo_seed.already_seeded", extra={"company": DEMO_COMPANY})
    return created
