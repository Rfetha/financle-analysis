from fastapi.testclient import TestClient
from sonar.api.app import create_app
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        return OhlcvSeries(
            symbol, interval,
            [Candle(ts=1, open=1.0, high=2.0, low=0.5, close=1.5, volume=10)],
            Provenance("fake", 1.0),
        )


async def _fake_analyzer(ticker: str):
    yield "analysis-step", {"section": "macro", "ok": True}
    yield "chart", {"ticker": ticker, "range": "6mo", "interval": "1d"}
    yield "text-delta", {"delta": "Rapor"}


def _client(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    app = create_app(registry=reg, cache=Cache(conn), analyzer=lambda: _fake_analyzer)
    return TestClient(app)


def test_ohlcv_endpoint_returns_candles(conn):
    r = _client(conn).get("/api/ohlcv/NVDA?range=6mo&interval=1d")
    assert r.status_code == 200
    assert r.json()["candles"][0]["close"] == 1.5


def test_analyze_streams_steps_and_done(conn):
    r = _client(conn).post("/api/analyze", json={"ticker": "NVDA"})
    assert r.status_code == 200
    body = r.text
    assert "event: analysis-step" in body
    assert "event: chart" in body
    assert "event: text-delta" in body
    assert body.rstrip().endswith("event: done\ndata: {}")
