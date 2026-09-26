from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings as app_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analytics import AnalyticsEvent
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


def upload_file(client: TestClient, filename: str, content: bytes) -> dict:
    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_event(
    db_session,
    *,
    query: str = "what is the policy?",
    success: bool = True,
    latency_ms: int = 25,
    document_names: list[str] | None = None,
    days_ago: int = 0,
) -> AnalyticsEvent:
    names = document_names if document_names is not None else []
    event = AnalyticsEvent(
        user_id=None,
        query=query,
        latency_ms=latency_ms,
        success=success,
        retrieved_documents=len(names),
        retrieved_document_names=names,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db_session.add(event)
    db_session.commit()
    return event


# --- access control ---------------------------------------------------------


def test_analytics_endpoints_reject_non_admins(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    register(client, "hr@orbit.test", role="HR")

    for path in (
        "/api/analytics/overview",
        "/api/analytics/daily",
        "/api/analytics/top-documents",
        "/api/analytics/top-queries",
        "/api/analytics/recent",
    ):
        response = client.get(path)
        assert response.status_code == 403, f"{path} -> {response.status_code}"


def test_analytics_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/analytics/overview")
    assert response.status_code == 401


def test_admin_can_read_all_endpoints(client: TestClient) -> None:
    register(client, "admin@orbit.test")

    for path in (
        "/api/analytics/overview",
        "/api/analytics/daily",
        "/api/analytics/top-documents",
        "/api/analytics/top-queries",
        "/api/analytics/recent",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"


# --- empty state ------------------------------------------------------------


def test_overview_starts_empty(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    payload = client.get("/api/analytics/overview").json()

    assert payload == {
        "total_queries": 0,
        "successful_queries": 0,
        "failed_queries": 0,
        "success_rate": 0.0,
        "avg_latency_ms": 0,
        "retrieved_documents_total": 0,
        "unique_users": 0,
    }


def test_daily_and_lists_start_empty(client: TestClient) -> None:
    register(client, "admin@orbit.test")

    daily = client.get("/api/analytics/daily").json()["days"]
    assert len(daily) == 14
    assert all(point["queries"] == 0 for point in daily)
    assert client.get("/api/analytics/top-documents").json() == {"documents": []}
    assert client.get("/api/analytics/top-queries").json() == {"queries": []}
    assert client.get("/api/analytics/recent").json() == {"searches": []}


# --- recording --------------------------------------------------------------


def test_successful_query_is_recorded(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    doc = upload_file(client, "handbook.txt", b"vacation policy twenty five days")
    assert client.post(f"/api/documents/{doc['id']}/index").status_code == 200

    response = client.post("/api/chat/query", json={"query": "vacation policy days"})
    assert response.status_code == 200, response.text
    cited = len(response.json()["sources"])

    overview = client.get("/api/analytics/overview").json()
    assert overview["total_queries"] == 1
    assert overview["successful_queries"] == 1
    assert overview["failed_queries"] == 0
    assert overview["success_rate"] == 100.0
    assert overview["unique_users"] == 1
    assert overview["retrieved_documents_total"] == cited
    assert overview["avg_latency_ms"] >= 0

    recent = client.get("/api/analytics/recent").json()["searches"]
    assert recent[0]["query"] == "vacation policy days"
    assert recent[0]["success"] is True
    assert recent[0]["retrieved_documents"] == cited

    today = client.get("/api/analytics/daily").json()["days"][-1]
    assert today["queries"] == 1
    assert today["successful"] == 1


def test_query_without_documents_records_success(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    response = client.post("/api/chat/query", json={"query": "anything at all?"})
    assert response.status_code == 200, response.text

    overview = client.get("/api/analytics/overview").json()
    assert overview["total_queries"] == 1
    assert overview["successful_queries"] == 1
    assert overview["retrieved_documents_total"] == 0

    recent = client.get("/api/analytics/recent").json()["searches"]
    assert recent[0]["retrieved_documents"] == 0


def test_failed_generation_is_recorded(client: TestClient, monkeypatch) -> None:
    register(client, "admin@orbit.test")
    doc = upload_file(client, "handbook.txt", b"vacation policy twenty five days")
    assert client.post(f"/api/documents/{doc['id']}/index").status_code == 200

    def _boom(query, passages):
        raise generator.GenerationError("Gemini is unavailable")

    monkeypatch.setattr(generator, "generate_answer", _boom)

    response = client.post("/api/chat/query", json={"query": "vacation policy"})
    assert response.status_code == 502

    overview = client.get("/api/analytics/overview").json()
    assert overview["total_queries"] == 1
    assert overview["successful_queries"] == 0
    assert overview["failed_queries"] == 1
    assert overview["success_rate"] == 0.0

    recent = client.get("/api/analytics/recent").json()["searches"]
    assert recent[0]["success"] is False
    assert recent[0]["retrieved_documents"] >= 1


def test_streaming_query_is_recorded(client: TestClient) -> None:
    register(client, "admin@orbit.test")
    doc = upload_file(client, "handbook.txt", b"vacation policy twenty five days")
    assert client.post(f"/api/documents/{doc['id']}/index").status_code == 200

    with client.stream(
        "POST",
        "/api/chat/query",
        json={"query": "vacation policy"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]
    assert any(line.startswith("event: done") for line in lines)

    overview = client.get("/api/analytics/overview").json()
    assert overview["total_queries"] == 1
    assert overview["successful_queries"] == 1


# --- aggregations -----------------------------------------------------------


def test_daily_groups_by_utc_day_and_zero_fills(client, db_session) -> None:
    register(client, "admin@orbit.test")
    make_event(db_session, query="today one")
    make_event(db_session, query="today two")
    make_event(db_session, query="yesterday", days_ago=1)
    make_event(db_session, query="older", days_ago=3, success=False)

    days = client.get("/api/analytics/daily?days=7").json()["days"]

    assert len(days) == 7
    assert days[0]["date"] < days[-1]["date"]
    assert days[-1]["queries"] == 2  # today
    assert days[-2]["queries"] == 1  # yesterday
    assert days[-4]["queries"] == 1  # three days ago
    assert days[-4]["failed"] == 1
    assert days[0]["queries"] == 0  # quiet day zero-filled
    assert sum(point["queries"] for point in days) == 4


def test_top_documents_counts_once_per_query(client, db_session) -> None:
    register(client, "admin@orbit.test")
    make_event(db_session, document_names=["a.txt", "a.txt", "b.txt"])
    make_event(db_session, document_names=["a.txt"])
    make_event(db_session, document_names=["c.txt"])

    documents = client.get("/api/analytics/top-documents").json()["documents"]

    assert documents[0] == {"document": "a.txt", "count": 2}
    assert [item["document"] for item in documents] == ["a.txt", "b.txt", "c.txt"]
    assert documents[1]["count"] == 1


def test_top_queries_counts_frequency(client, db_session) -> None:
    register(client, "admin@orbit.test")
    make_event(db_session, query="how many days?")
    make_event(db_session, query="how many days?")
    make_event(db_session, query="how many days?")
    make_event(db_session, query="something else")

    queries = client.get("/api/analytics/top-queries").json()["queries"]

    assert queries[0] == {"query": "how many days?", "count": 3}
    assert queries[1] == {"query": "something else", "count": 1}


def test_recent_returns_newest_first(client, db_session) -> None:
    register(client, "admin@orbit.test")
    make_event(db_session, query="oldest", days_ago=2)
    make_event(db_session, query="newest")
    make_event(db_session, query="middle", days_ago=1)

    searches = client.get("/api/analytics/recent").json()["searches"]

    assert [item["query"] for item in searches] == ["newest", "middle", "oldest"]
    assert searches[0]["created_at"]
