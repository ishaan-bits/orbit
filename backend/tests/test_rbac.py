from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings as app_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth import Role
from app.rag import generator, reranker
from app.services.auth import ensure_rbac_seed
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


@pytest.fixture()
def rbac_seed(db_session):
    ensure_rbac_seed(db_session)
    return db_session


@pytest.fixture()
def uploads_dir(tmp_path: Path) -> Path:
    path = tmp_path / "uploads"
    path.mkdir()
    return path


@pytest.fixture()
def chroma_dir(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "chroma_db"
    monkeypatch.setattr(app_settings, "chroma_path", str(path))
    return path


@pytest.fixture()
def fake_embedder(monkeypatch) -> None:
    def _encode(texts):
        return [
            [float(len(text)), float(sum(ord(c) for c in text) % 101), 1.0]
            for text in texts
        ]

    monkeypatch.setattr("app.rag.embedder.encode_texts", _encode)


@pytest.fixture()
def fake_reranker(monkeypatch) -> None:
    class FakeCrossEncoder:
        def predict(self, pairs):
            return [float(len(text)) for _query, text in pairs]

    monkeypatch.setattr(reranker, "get_model", lambda: FakeCrossEncoder())


@pytest.fixture()
def fake_generator(monkeypatch) -> None:
    monkeypatch.setattr(
        generator, "generate_answer", lambda query, passages: "**Hello** world"
    )
    monkeypatch.setattr(
        generator,
        "stream_answer",
        lambda query, passages: iter(["**Hello** ", "world"]),
    )


@pytest.fixture()
def client(
    db_session,
    uploads_dir: Path,
    chroma_dir: Path,
    fake_embedder,
    fake_reranker,
    fake_generator,
    rbac_seed,
):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_uploads_dir] = lambda: uploads_dir

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# --- helpers ----------------------------------------------------------------


def register(client: TestClient, email: str, role: str | None = None) -> dict:
    body = {"email": email, "password": "password123"}
    if role is not None:
        body["role"] = role
    response = client.post("/api/auth/register", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_folder(client: TestClient, name: str, allowed_roles=None) -> dict:
    body: dict = {"name": name}
    if allowed_roles is not None:
        body["allowed_roles"] = allowed_roles
    response = client.post("/api/folders", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def upload_file(
    client: TestClient, filename: str, content: bytes, folder_id: str | None = None
) -> dict:
    data: dict = {}
    if folder_id is not None:
        data["folder_id"] = folder_id
    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, content, "text/plain")},
        data=data,
    )
    assert response.status_code == 201, response.text
    return response.json()


def index_document(client: TestClient, document_id: str) -> dict:
    response = client.post(f"/api/documents/{document_id}/index")
    assert response.status_code == 200, response.text
    return response.json()


def ask(client: TestClient, query: str, conversation_id: str | None = None) -> dict:
    body: dict = {"query": query}
    if conversation_id is not None:
        body["conversation_id"] = conversation_id
    response = client.post("/api/chat/query", json=body)
    assert response.status_code == 200, response.text
    return response.json()


# --- seeding ----------------------------------------------------------------


def test_default_roles_are_seeded(db_session, rbac_seed) -> None:
    ensure_rbac_seed(db_session)  # idempotent re-run
    names = {role.name for role in db_session.scalars(select(Role))}
    assert names == {"Admin", "HR", "Engineering"}


def test_general_folder_is_seeded_for_all_roles(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    response = client.get("/api/folders")

    general = next(f for f in response.json() if f["name"] == "General")
    assert set(general["allowed_roles"]) == {"Admin", "HR", "Engineering"}


# --- folder role visibility -------------------------------------------------


def test_folder_roles_scope_document_and_folder_visibility(
    client: TestClient,
) -> None:
    admin = register(client, "admin@orbit.test")
    assert admin["role"] == "Admin"

    hr_folder = create_folder(client, "HR Policies", ["Admin", "HR"])
    eng_folder = create_folder(client, "Engineering", ["Admin", "Engineering"])
    hr_doc = upload_file(
        client, "handbook.txt", b"HR handbook", folder_id=hr_folder["id"]
    )
    eng_doc = upload_file(
        client, "runbook.txt", b"eng runbook", folder_id=eng_folder["id"]
    )

    # HR user: sees the HR folder + its documents only
    register(client, "hr@orbit.test", role="HR")
    hr_folders = {f["name"] for f in client.get("/api/folders").json()}
    assert hr_folders == {"General", "HR Policies"}
    hr_docs = {d["id"] for d in client.get("/api/documents").json()["items"]}
    assert hr_doc["id"] in hr_docs
    assert eng_doc["id"] not in hr_docs

    # Engineering user: mirror image
    register(client, "eng@orbit.test", role="Engineering")
    eng_folders = {f["name"] for f in client.get("/api/folders").json()}
    assert eng_folders == {"General", "Engineering"}
    eng_docs = {d["id"] for d in client.get("/api/documents").json()["items"]}
    assert eng_doc["id"] in eng_docs
    assert hr_doc["id"] not in eng_docs


def test_upload_into_forbidden_folder_returns_403(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    hr_only = create_folder(client, "HR Only", ["Admin", "HR"])

    register(client, "eng@orbit.test", role="Engineering")
    forbidden = client.post(
        "/api/documents/upload",
        files={"file": ("sneak.txt", b"content", "text/plain")},
        data={"folder_id": hr_only["id"]},
    )
    assert forbidden.status_code == 403

    # general-folder uploads still work for everyone
    allowed = client.post(
        "/api/documents/upload",
        files={"file": ("mine.txt", b"content", "text/plain")},
    )
    assert allowed.status_code == 201
    assert allowed.json()["folder_name"] == "General"


def test_opening_forbidden_document_returns_403(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    folder = create_folder(client, "Admin Board", ["Admin"])
    doc = upload_file(client, "secret.txt", b"secret", folder_id=folder["id"])

    register(client, "hr@orbit.test", role="HR")
    assert client.get(f"/api/documents/{doc['id']}").status_code == 403
    assert client.get(f"/api/documents/{doc['id']}/file").status_code == 403
    assert client.post(f"/api/documents/{doc['id']}/index").status_code == 403
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 403


# --- document permission grants --------------------------------------------


def test_document_permission_grant_overrides_folder(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    folder = create_folder(client, "Sealed", ["Admin"])
    doc = upload_file(client, "sealed.txt", b"sealed content", folder_id=folder["id"])

    register(client, "hr@orbit.test", role="HR")
    assert doc["id"] not in {
        d["id"] for d in client.get("/api/documents").json()["items"]
    }

    # Admin grants HR read access to this one document
    login(client, "admin@orbit.test")
    grant = client.post(
        "/api/permissions", json={"document_id": doc["id"], "role": "HR"}
    )
    assert grant.status_code == 201, grant.text

    login(client, "hr@orbit.test")
    assert doc["id"] in {d["id"] for d in client.get("/api/documents").json()["items"]}
    assert client.get(f"/api/documents/{doc['id']}").status_code == 200

    # Revocation restores folder rules
    login(client, "admin@orbit.test")
    revoke = client.request(
        "DELETE",
        "/api/permissions",
        json={"document_id": doc["id"], "role": "HR"},
    )
    assert revoke.status_code == 200, revoke.text

    login(client, "hr@orbit.test")
    assert doc["id"] not in {
        d["id"] for d in client.get("/api/documents").json()["items"]
    }


def test_permission_grant_requires_admin(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    doc = upload_file(client, "a.txt", b"a")

    register(client, "hr@orbit.test", role="HR")
    response = client.post(
        "/api/permissions", json={"document_id": doc["id"], "role": "Engineering"}
    )
    assert response.status_code == 403
    revoke = client.request(
        "DELETE",
        "/api/permissions",
        json={"document_id": doc["id"], "role": "Engineering"},
    )
    assert revoke.status_code == 403


# --- chat scoping and retrieval filtering -----------------------------------


def test_chat_history_is_isolated_per_user(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    payload = ask(client, "hello orbit")
    conversation_id = payload["conversation_id"]

    admin_history = client.get("/api/chat/history").json()["conversations"]
    assert len(admin_history) == 1
    assert admin_history[0]["id"] == conversation_id

    # A second user starts fresh and cannot touch the first user's conversation
    register(client, "hr@orbit.test", role="HR")
    assert client.get("/api/chat/history").json()["conversations"] == []
    hijack = client.post(
        "/api/chat/query",
        json={"query": "continue", "conversation_id": conversation_id},
    )
    assert hijack.status_code == 404


def test_retrieval_sources_filtered_by_folder_role(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    hr_folder = create_folder(client, "HR Policies", ["Admin", "HR"])
    eng_folder = create_folder(client, "Engineering", ["Admin", "Engineering"])
    hr_doc = upload_file(
        client,
        "handbook.txt",
        b"The vacation policy grants twenty five days of paid leave per year.",
        folder_id=hr_folder["id"],
    )
    eng_doc = upload_file(
        client,
        "runbook.txt",
        b"The deploy pipeline runs integration tests before every release.",
        folder_id=eng_folder["id"],
    )
    index_document(client, hr_doc["id"])
    index_document(client, eng_doc["id"])

    # Engineering user: matching content from the HR folder is dropped
    register(client, "eng@orbit.test", role="Engineering")
    allowed = ask(client, "deploy pipeline release tests")
    assert {s["document"] for s in allowed["sources"]} == {"runbook.txt"}

    # A query that only matches the forbidden document never leaks its name
    blocked = ask(client, "vacation policy paid leave")
    assert "handbook.txt" not in {s["document"] for s in blocked["sources"]}
    assert blocked["conversation_id"]

    # Admin sees both documents
    login(client, "admin@orbit.test")
    admin_query = ask(client, "vacation policy paid leave")
    assert "handbook.txt" in {s["document"] for s in admin_query["sources"]}
