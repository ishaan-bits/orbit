from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.security import verify_password
from app.db.base import Base
from app.models.auth import Role, User
from app.models.knowledge import Folder
from app.services.auth import authenticate, can_access_folder, ensure_rbac_seed
from app.services.demo_seed import (
    DEMO_FOLDERS,
    DEMO_PASSWORD,
    DEMO_USERS,
    ensure_demo_seed,
    should_seed_demo,
)
from app.services.errors import InvalidCredentialsError
from app.services.storage import get_uploads_dir

# --- fixtures ---------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = testing_session()
    yield session
    session.close()


# --- seed behaviour ---------------------------------------------------------


def test_seed_creates_company_folders_and_users(db_session) -> None:
    created = ensure_demo_seed(db_session)

    assert set(created["folders"]) == set(DEMO_FOLDERS)
    assert set(created["users"]) == {email for email, _, _ in DEMO_USERS}

    folder_names = set(db_session.scalars(select(Folder.name)).all())
    assert set(DEMO_FOLDERS) <= folder_names
    assert "General" in folder_names

    emails = set(db_session.scalars(select(User.email)).all())
    assert emails == {email for email, _, _ in DEMO_USERS}


def test_seed_creates_users_with_the_shared_password(db_session) -> None:
    ensure_demo_seed(db_session)

    for email, role_name, _ in DEMO_USERS:
        user = authenticate(db_session, email, DEMO_PASSWORD)
        assert user.role.name == role_name
        assert verify_password(DEMO_PASSWORD, user.hashed_password)


def test_seed_is_idempotent(db_session) -> None:
    first = ensure_demo_seed(db_session)
    second = ensure_demo_seed(db_session)

    assert first["users"] and first["folders"]
    assert second == {"folders": [], "users": []}

    user_count = db_session.scalar(select(func.count()).select_from(User))
    folder_count = db_session.scalar(select(func.count()).select_from(Folder))
    assert int(user_count) == len(DEMO_USERS)
    assert int(folder_count) == len(DEMO_FOLDERS) + 1  # + General


def test_seed_never_overwrites_existing_rows(db_session) -> None:
    ensure_rbac_seed(db_session)
    admin_role = db_session.scalar(select(Role).where(Role.name == "Admin"))
    db_session.add(Folder(name="HR", allowed_roles=[admin_role]))
    db_session.add(
        User(
            email="admin@novatech.com",
            hashed_password="already-hashed",
            role_id=admin_role.id,
        )
    )
    db_session.commit()

    created = ensure_demo_seed(db_session)

    assert "HR" not in created["folders"]
    assert "admin@novatech.com" not in created["users"]
    user = db_session.scalar(select(User).where(User.email == "admin@novatech.com"))
    assert user.hashed_password == "already-hashed"
    with pytest.raises(InvalidCredentialsError):
        authenticate(db_session, "admin@novatech.com", DEMO_PASSWORD)


def test_demo_folders_match_the_documented_rbac_matrix(db_session) -> None:
    ensure_demo_seed(db_session)

    hr = db_session.scalar(select(User).where(User.email == "hr@novatech.com"))
    eng = db_session.scalar(select(User).where(User.email == "eng@novatech.com"))
    admin = db_session.scalar(select(User).where(User.email == "admin@novatech.com"))
    folders = db_session.scalars(select(Folder)).all()

    hr_visible = {f.name for f in folders if can_access_folder(hr, f)}
    eng_visible = {f.name for f in folders if can_access_folder(eng, f)}
    admin_visible = {f.name for f in folders if can_access_folder(admin, f)}

    assert hr_visible == {"General", "HR", "Legal"}
    assert eng_visible == {"General", "Engineering", "Product", "Security"}
    assert admin_visible == {f.name for f in folders}


# --- configuration ----------------------------------------------------------


def test_cors_origins_accept_comma_separated_string() -> None:
    settings = Settings(cors_origins="https://orbit.vercel.app, http://localhost:3000")
    assert settings.cors_origins == [
        "https://orbit.vercel.app",
        "http://localhost:3000",
    ]


def test_cors_origins_accept_json_list_string() -> None:
    settings = Settings(cors_origins='["https://orbit.vercel.app"]')
    assert settings.cors_origins == ["https://orbit.vercel.app"]


def test_uploads_dir_setting_overrides_default(tmp_path, monkeypatch) -> None:
    from app.core.config import settings as app_settings

    custom = tmp_path / "custom-uploads"
    monkeypatch.setattr(app_settings, "uploads_dir", str(custom))
    assert get_uploads_dir() == custom
    assert custom.is_dir()


# --- seed gating (SEED_DEMO tri-state) --------------------------------------


def test_should_seed_demo_true_when_explicitly_enabled() -> None:
    assert should_seed_demo(True, 0) is True
    assert should_seed_demo(True, 5) is True  # idempotent re-seed


def test_should_seed_demo_false_when_disabled() -> None:
    assert should_seed_demo(False, 0) is False
    assert should_seed_demo(False, 5) is False


def test_should_seed_demo_auto_seeds_only_empty_database() -> None:
    assert should_seed_demo(None, 0) is True  # first run
    assert should_seed_demo(None, 3) is False  # populated database
