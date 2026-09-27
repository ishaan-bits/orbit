import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import SESSION_COOKIE
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth import User
from app.services.auth import ensure_rbac_seed

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


@pytest.fixture()
def rbac_seed(db_session):
    ensure_rbac_seed(db_session)
    return db_session


@pytest.fixture()
def client(db_session, rbac_seed):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _register(client: TestClient, **overrides) -> dict:
    body = {
        "email": "admin@orbit.test",
        "password": "password123",
        "full_name": "Orbit Admin",
    }
    body.update(overrides)
    return client.post("/api/auth/register", json=body)


# --- register ---------------------------------------------------------------


def test_register_creates_user_and_sets_httponly_cookie(client: TestClient) -> None:
    response = _register(client)

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["email"] == "admin@orbit.test"
    assert payload["full_name"] == "Orbit Admin"
    assert payload["role"] == "Admin"
    assert payload["is_active"] is True
    uuid_checked = payload["id"]
    assert uuid_checked

    cookie_header = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookie_header if c.startswith(SESSION_COOKIE))
    lowered = session_cookie.lower()
    # Production session contract (Vercel + Render): cross-site, host-only,
    #7-day, partitioned (CHIPS) so WebKit/Chrome don't drop it
    assert "httponly" in lowered
    assert "samesite=none" in lowered
    assert "secure" in lowered
    assert "max-age=604800" in lowered
    assert "domain=" not in lowered
    assert "path=/" in lowered
    assert "partitioned" in lowered


def test_register_normalises_email(client: TestClient) -> None:
    response = _register(client, email="  Admin@Orbit.TEST ")

    assert response.status_code == 201
    assert response.json()["email"] == "admin@orbit.test"


def test_first_user_is_admin_second_defaults_engineering(
    client: TestClient,
) -> None:
    assert _register(client).json()["role"] == "Admin"

    second = _register(client, email="dev@orbit.test")
    assert second.status_code == 201
    assert second.json()["role"] == "Engineering"


def test_register_can_choose_hr_role(client: TestClient) -> None:
    _register(client)
    response = _register(client, email="hr@orbit.test", role="HR")

    assert response.status_code == 201
    assert response.json()["role"] == "HR"


def test_register_rejects_admin_role_after_bootstrap(client: TestClient) -> None:
    _register(client)
    response = _register(client, email="sneaky@orbit.test", role="Admin")

    assert response.status_code == 400
    assert "Admin" in response.json()["detail"]


def test_register_rejects_unknown_role(client: TestClient) -> None:
    _register(client)
    response = _register(client, email="x@orbit.test", role="Marketing")

    assert response.status_code == 400


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client)
    response = _register(client)

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = _register(client, password="short")

    assert response.status_code == 422


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = _register(client, email="not-an-email")

    assert response.status_code == 422


def test_password_is_stored_hashed(client: TestClient, db_session) -> None:
    _register(client)

    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == "admin@orbit.test"))
    assert user is not None
    assert user.hashed_password != "password123"
    assert user.hashed_password.startswith("$2")


# --- login / me / logout ----------------------------------------------------


def test_login_me_logout_flow(client: TestClient) -> None:
    _register(client)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"email": "admin@orbit.test", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["email"] == "admin@orbit.test"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "Admin"


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    _register(client)
    client.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@orbit.test", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_returns_same_error(client: TestClient) -> None:
    _register(client)
    client.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@orbit.test", "password": "password123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session_cookie(client: TestClient) -> None:
    _register(client)
    assert client.get("/api/auth/me").status_code == 200

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    cleared = next(
        c
        for c in response.headers.get_list("set-cookie")
        if c.startswith(SESSION_COOKIE)
    )
    assert "max-age=0" in cleared.lower()
    assert "partitioned" in cleared.lower()
    assert "httponly" in cleared.lower()
    assert "samesite=none" in cleared.lower()
    assert client.get("/api/auth/me").status_code == 401


def test_bearer_header_is_accepted_as_fallback(client: TestClient) -> None:
    _register(client)
    cookieless = TestClient(app)
    # reuse the token from the authenticated client's cookie
    token = client.cookies.get(SESSION_COOKIE)
    assert token

    response = cookieless.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "admin@orbit.test"


# --- protected API surface --------------------------------------------------


def test_protected_endpoints_require_authentication(db_session, rbac_seed) -> None:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        anonymous = TestClient(app)
        assert anonymous.get("/api/documents").status_code == 401
        assert anonymous.get("/api/folders").status_code == 401
        assert anonymous.get("/api/chat/history").status_code == 401
        assert (
            anonymous.post("/api/chat/query", json={"query": "hello"}).status_code
            == 401
        )
        assert (
            anonymous.post(
                "/api/documents/upload",
                files={"file": ("a.txt", b"x", "text/plain")},
            ).status_code
            == 401
        )
        assert anonymous.post("/api/permissions", json={}).status_code == 401
    finally:
        app.dependency_overrides.clear()
