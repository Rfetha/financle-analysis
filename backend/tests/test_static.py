from pathlib import Path
from fastapi.testclient import TestClient
from sonar.api.app import create_app


def test_root_serves_index_when_static_exists():
    static = Path(__file__).parent.parent / "sonar" / "web" / "static" / "index.html"
    client = TestClient(create_app())
    resp = client.get("/")
    if static.exists():
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
    else:
        assert resp.status_code in (404, 200)  # build yapılmadıysa tolere et
