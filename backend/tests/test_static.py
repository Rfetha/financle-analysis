from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sonar.api.app import create_app


def test_root_serves_index_when_static_exists():
    static = Path(__file__).parent.parent / "sonar" / "web" / "static" / "index.html"
    if not static.exists():
        pytest.skip("frontend build yok (sonar/web/static/index.html)")
    resp = TestClient(create_app()).get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
