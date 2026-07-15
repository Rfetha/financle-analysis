import threading

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


def test_throttle_is_thread_safe_under_concurrent_calls():
    # Why: DeepAnalysis paralel thread'lerde tek HttpClient paylaşıyor (I1);
    # lock olmadan iki thread aynı stale self._last'i okuyup ikisi de
    # beklemeden geçebilir. clock yalnız sleep() cagrisiyla ilerliyor, bu
    # yuzden dogru serilestirme olmadan asagidaki assertion'lar tutmaz.
    clock_lock = threading.Lock()
    clock = {"t": 0.0}
    slept = []

    def handler(request):
        return httpx.Response(200, json={})

    def fake_now():
        with clock_lock:
            return clock["t"]

    def fake_sleep(d):
        with clock_lock:
            slept.append(d)
            clock["t"] += d

    n = 8
    client = HttpClient(
        "Sonar/0.1 (test@example.com)",
        min_interval=0.1,
        transport=httpx.MockTransport(handler),
        now=fake_now,
        sleep=fake_sleep,
    )

    threads = [
        threading.Thread(target=client.get_json, args=("https://data.sec.gov/x",)) for _ in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # İlk istek beklemez, kalan n-1 istek her biri tam min_interval bekler —
    # yani hiçbiri aradan zaman geçmeden (burst) geçmez.
    assert slept == [0.1] * (n - 1)
    assert sum(slept) >= (n - 1) * 0.1


def test_http_error_propagates():
    client = HttpClient(
        "Sonar/0.1 (t@e.com)",
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
        retries=0,
    )
    with pytest.raises(httpx.HTTPStatusError):
        client.get_json("https://data.sec.gov/x")
