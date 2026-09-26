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
