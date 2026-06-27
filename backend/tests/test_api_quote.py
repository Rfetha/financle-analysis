from fastapi.testclient import TestClient
from sonar.api.app import create_app
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.store.cache import Cache
from sonar.store.db import connect


def _client(tmp_path):
    reg = MarketRegistry()
    reg.register(USMarketPlugin(now=lambda: 1.0, fetch=lambda t: (110.0, 100.0)))
    cache = Cache(connect(tmp_path / "t.db"), now=lambda: 1.0)
    return TestClient(create_app(registry=reg, cache=cache))


def test_quote_endpoint_returns_computed_quote(tmp_path):
    resp = _client(tmp_path).get("/api/quote/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert body["change_pct"] == 10.0


def test_quote_endpoint_unknown_symbol_returns_404(tmp_path):
    def _bad_fetch(t):
        raise KeyError("exchangeTimezoneName")
    reg = MarketRegistry()
    reg.register(USMarketPlugin(now=lambda: 1.0, fetch=_bad_fetch))
    cache = Cache(connect(tmp_path / "t2.db"), now=lambda: 1.0)
    resp = TestClient(create_app(registry=reg, cache=cache)).get("/api/quote/ZZZZQ")
    assert resp.status_code == 404
