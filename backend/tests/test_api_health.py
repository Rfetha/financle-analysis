from fastapi.testclient import TestClient
from sonar.api.app import create_app


def test_health_returns_ok():
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
