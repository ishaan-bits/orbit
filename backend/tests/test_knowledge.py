import uuid
from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.knowledge import Document
from app.rag import vectordb
from app.services.storage import get_uploads_dir


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
def uploads_dir(tmp_path: Path) -> Path:
    path = tmp_path / "uploads"
    path.mkdir()
    return path


@pytest.fixture()
def client(db_session, uploads_dir: Path, rbac_seed):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_uploads_dir] = lambda: uploads_dir

    with TestClient(app, base_url="https://testserver") as test_client:
        response = test_client.post(
            "/api/auth/register",
            json={"email": "admin@orbit.test", "password": "password123"},
        )
        assert response.status_code == 201, response.text
        yield test_client

    app.dependency_overrides.clear()


def upload_file(
    client: TestClient,
    filename: str = "report.pdf",
    content: bytes = b"%PDF-1.4 orbit",
    content_type: str = "application/pdf",
    folder_id: Optional[str] = None,
):
    data: dict[str, Any] = {}
    if folder_id is not None:
        data["folder_id"] = folder_id
    return client.post(
        "/api/documents/upload",
        files={"file": (filename, content, content_type)},
        data=data,
    )


def create_folder(client: TestClient, name: str) -> dict[str, Any]:
    response = client.post("/api/folders", json={"name": name})
    assert response.status_code == 201
    return response.json()


# --- folders ---------------------------------------------------------------


def test_create_folder_returns_metadata(client: TestClient) -> None:
    response = client.post("/api/folders", json={"name": "  Contracts  "})

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Contracts"
    assert payload["document_count"] == 0
    assert payload["created_at"]
    uuid.UUID(payload["id"])


def test_create_folder_rejects_duplicate_names(client: TestClient) -> None:
    create_folder(client, "Research")

    response = client.post("/api/folders", json={"name": "research"})
    assert response.status_code == 409


def test_create_folder_rejects_blank_name(client: TestClient) -> None:
    response = client.post("/api/folders", json={"name": "   "})
    assert response.status_code == 422


def test_list_folders_seeded_with_general(client: TestClient) -> None:
    response = client.get("/api/folders")

    assert response.status_code == 200
    payload = response.json()
    assert [folder["name"] for folder in payload] == ["General"]
    assert payload[0]["document_count"] == 0
    assert set(payload[0]["allowed_roles"]) == {"Admin", "HR", "Engineering"}


def test_list_folders_includes_document_counts(client: TestClient) -> None:
    folder = create_folder(client, "Policies")
    upload_file(client, "policy.pdf", folder_id=folder["id"])
    upload_file(client, "policy-v2.docx", b"PK\x03\x04docx", folder_id=folder["id"])
    upload_file(client, "outside.txt", b"no folder")

    response = client.get("/api/folders")

    assert response.status_code == 200
    payload = response.json()
    by_name = {item["name"]: item for item in payload}
    assert by_name["Policies"]["document_count"] == 2
    assert by_name["General"]["document_count"] == 1


# --- upload ----------------------------------------------------------------


def test_upload_pdf_returns_metadata(client: TestClient, uploads_dir: Path) -> None:
    content = b"%PDF-1.4 orbit knowledge base"
    response = upload_file(client, "Q3 Report.pdf", content)

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "Q3 Report.pdf"
    assert payload["file_extension"] == "pdf"
    assert payload["mime_type"] == "application/pdf"
    assert payload["file_size"] == len(content)
    # uploads without a folder land in the shared General folder
    assert payload["folder_id"]
    assert payload["folder_name"] == "General"
    assert payload["created_at"]
    uuid.UUID(payload["id"])

    stored = list(uploads_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].name != "Q3 Report.pdf"
    assert stored[0].suffix == ".pdf"
    uuid.UUID(stored[0].stem)
    assert stored[0].read_bytes() == content


@pytest.mark.parametrize(
    ("filename", "content_type", "extension"),
    [
        ("guide.pdf", "application/pdf", "pdf"),
        (
            "handbook.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        ),
        ("notes.txt", "text/plain", "txt"),
        ("readme.md", "text/markdown", "md"),
    ],
)
def test_upload_accepts_supported_types(
    client: TestClient, filename: str, content_type: str, extension: str
) -> None:
    response = upload_file(client, filename, b"payload", content_type)

    assert response.status_code == 201
    assert response.json()["file_extension"] == extension


def test_upload_into_folder_resolves_folder_name(client: TestClient) -> None:
    folder = create_folder(client, "Legal")

    response = upload_file(client, "nda.txt", b"agreement", folder_id=folder["id"])

    assert response.status_code == 201
    payload = response.json()
    assert payload["folder_id"] == folder["id"]
    assert payload["folder_name"] == "Legal"


def test_upload_rejects_unsupported_extension(
    client: TestClient, uploads_dir: Path
) -> None:
    response = upload_file(
        client, "virus.exe", b"MZ", content_type="application/octet-stream"
    )

    assert response.status_code == 415
    assert list(uploads_dir.iterdir()) == []


def test_upload_rejects_mismatched_mime_type(client: TestClient) -> None:
    response = upload_file(
        client,
        "script.txt",
        b"echo hi",
        content_type="application/x-msdownload",
    )

    assert response.status_code == 415


def test_upload_rejects_oversized_file(client: TestClient, uploads_dir: Path) -> None:
    oversized = b"a" * (25 * 1024 * 1024 + 1)
    response = upload_file(client, "big.pdf", oversized)

    assert response.status_code == 413
    assert list(uploads_dir.iterdir()) == []


def test_upload_rejects_empty_file(client: TestClient, uploads_dir: Path) -> None:
    response = upload_file(client, "empty.txt", b"", content_type="text/plain")

    assert response.status_code == 400
    assert list(uploads_dir.iterdir()) == []


def test_upload_unknown_folder_returns_404(client: TestClient) -> None:
    response = upload_file(client, "notes.txt", b"hi", folder_id="missing-id")

    assert response.status_code == 404


# --- list / search ---------------------------------------------------------


def test_list_documents_returns_all_active(client: TestClient) -> None:
    upload_file(client, "alpha.pdf", b"a")
    upload_file(client, "beta.docx", b"b")

    response = client.get("/api/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    names = {item["original_filename"] for item in payload["items"]}
    assert names == {"alpha.pdf", "beta.docx"}


def test_list_documents_filters_by_folder(client: TestClient) -> None:
    folder = create_folder(client, "Finance")
    upload_file(client, "budget.txt", b"1", folder_id=folder["id"])
    upload_file(client, "other.txt", b"2")

    response = client.get(f"/api/documents?folder_id={folder['id']}")

    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["original_filename"] == "budget.txt"


def test_list_documents_search_is_case_insensitive(client: TestClient) -> None:
    upload_file(client, "Quarterly Review.md", b"# notes")
    upload_file(client, "unrelated.txt", b"x")

    response = client.get("/api/documents", params={"q": "quarterly"})

    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["original_filename"] == "Quarterly Review.md"


def test_list_documents_search_escapes_wildcards(client: TestClient) -> None:
    upload_file(client, "100% legit.txt", b"x")
    upload_file(client, "100 legit.txt", b"y")

    response = client.get("/api/documents", params={"q": "100%"})

    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["original_filename"] == "100% legit.txt"


def test_get_document_returns_metadata(client: TestClient) -> None:
    created = upload_file(client, "spec.md", b"# spec").json()

    response = client.get(f"/api/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["original_filename"] == "spec.md"


def test_get_unknown_document_returns_404(client: TestClient) -> None:
    response = client.get("/api/documents/does-not-exist")
    assert response.status_code == 404


# --- delete ----------------------------------------------------------------


def test_delete_document_soft_deletes_and_removes_file(
    client: TestClient,
    db_session,
    uploads_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = upload_file(
        client, "obsolete.txt", b"bye", content_type="text/plain"
    ).json()
    assert len(list(uploads_dir.iterdir())) == 1

    vector_calls: list[str] = []
    monkeypatch.setattr(vectordb, "get_collection", lambda: "test-collection")
    monkeypatch.setattr(
        vectordb,
        "delete_document_vectors",
        lambda _collection, doc_id: vector_calls.append(doc_id),
    )

    response = client.delete(f"/api/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"id": created["id"], "status": "deleted"}

    # physical file removed
    assert list(uploads_dir.iterdir()) == []

    # chroma vectors for the document removed
    assert vector_calls == [created["id"]]

    # soft-deleted row retained with a deletion timestamp
    row = db_session.get(Document, created["id"])
    assert row is not None
    assert row.deleted_at is not None

    # excluded from list and detail endpoints
    assert client.get("/api/documents").json()["total"] == 0
    assert client.get(f"/api/documents/{created['id']}").status_code == 404


def test_delete_document_twice_returns_404(client: TestClient) -> None:
    created = upload_file(client, "once.txt", b"1").json()

    assert client.delete(f"/api/documents/{created['id']}").status_code == 200
    assert client.delete(f"/api/documents/{created['id']}").status_code == 404


# --- file streaming --------------------------------------------------------


def test_file_endpoint_streams_original_bytes(client: TestClient) -> None:
    payload = b"%PDF-1.4 orbit viewer content"
    created = upload_file(client, "viewer.pdf", payload).json()

    response = client.get(f"/api/documents/{created['id']}/file")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "viewer.pdf" in response.headers["content-disposition"]
    assert response.content == payload


def test_file_endpoint_derives_mime_from_extension(client: TestClient) -> None:
    created = upload_file(
        client,
        "report.pdf",
        b"%PDF-1.4 generic",
        content_type="application/octet-stream",
    ).json()

    response = client.get(f"/api/documents/{created['id']}/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_file_endpoint_requires_auth(client: TestClient) -> None:
    created = upload_file(client, "private.pdf").json()

    client.cookies.clear()
    response = client.get(f"/api/documents/{created['id']}/file")

    assert response.status_code == 401


def test_file_endpoint_returns_404_for_unknown_document(client: TestClient) -> None:
    response = client.get("/api/documents/does-not-exist/file")
    assert response.status_code == 404


def test_file_endpoint_returns_404_when_stored_file_missing(
    client: TestClient, db_session, uploads_dir: Path
) -> None:
    created = upload_file(client, "vanished.pdf").json()
    row = db_session.get(Document, created["id"])
    assert row is not None
    (uploads_dir / row.stored_filename).unlink()

    response = client.get(f"/api/documents/{created['id']}/file")

    assert response.status_code == 404
