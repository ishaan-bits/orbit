from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_payload_shape() -> None:
    response = client.get("/api/health")
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "Orbit"
    assert payload["version"]
    assert payload["environment"]
    assert payload["timestamp"]
    assert payload["checks"]["database"] == "up"


def test_health_reports_rss_mb() -> None:
    payload = client.get("/api/health").json()

    assert isinstance(payload["rss_mb"], int)
    assert payload["rss_mb"] > 0


def test_health_reports_embedding_state() -> None:
    payload = client.get("/api/health").json()

    assert payload["embedding_provider"] in {"local", "gemini"}
    assert payload["embedding_fallback"] in {"local", "none"}
    assert isinstance(payload["gemini_key_configured"], bool)
    assert isinstance(payload["local_model_loaded"], bool)


def test_health_reports_last_retry_at() -> None:
    payload = client.get("/api/health").json()

    assert "last_retry_at" in payload
    assert payload["last_retry_at"] is None or isinstance(
        payload["last_retry_at"], str
    )
