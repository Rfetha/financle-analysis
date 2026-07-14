import httpx
import pytest
from sonar.market.sources.http import HttpClient


def test_sends_user_agent():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, json={"ok": True})

    client = HttpClient("Sonar/0.1 (test@example.com)", transport=httpx.MockTransport(handler))
    assert client.get_json("https://data.sec.gov/x") == {"ok": True}
    assert seen["ua"] == "Sonar/0.1 (test@example.com)"


def test_rate_limit_sleeps_between_calls():
    clock = {"t": 0.0}
    slept = []

    def handler(request):
        return httpx.Response(200, json={})

    client = HttpClient(
        "Sonar/0.1 (test@example.com)",
        min_interval=0.1,
        transport=httpx.MockTransport(handler),
        now=lambda: clock["t"],
        sleep=slept.append,
    )
    client.get_json("https://data.sec.gov/a")
    client.get_json("https://data.sec.gov/b")
    assert slept == [0.1]  # ikinci çağrı, aradan zaman geçmediği için bekledi


def test_http_error_propagates():
    client = HttpClient(
        "Sonar/0.1 (t@e.com)",
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
        retries=0,
    )
    with pytest.raises(httpx.HTTPStatusError):
        client.get_json("https://data.sec.gov/x")
