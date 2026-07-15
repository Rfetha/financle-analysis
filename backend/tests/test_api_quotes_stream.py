import pytest
from fastapi.testclient import TestClient
from sonar.agent import events
from sonar.api.app import create_app
from sonar.api.quotes import quote_stream
import sonar.api.quotes as quotes_module
from sonar.domain.money import Money
from sonar.domain.quote import Provenance, Quote
from sonar.market.base import BaseMarketPlugin, UnknownSymbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from decimal import Decimal


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_quote(self, symbol):
        if symbol.ticker == "ZZZZ":
            raise UnknownSymbol("ZZZZ")
        return Quote(
            symbol=symbol,
            price=Money(Decimal("180.42"), "USD"),
            previous_close=Money(Decimal("175.00"), "USD"),
            provenance=Provenance("alpaca", 1.0),
        )


def _ctx(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    return {"registry": reg, "cache": Cache(conn)}


@pytest.mark.asyncio
async def test_quote_stream_emits_tick_per_ticker(conn):
    ticks = [
        data
        async for etype, data in quote_stream(
            ["NVDA", "AAPL"], **_ctx(conn), interval=0, limit=1
        )
    ]
    assert [t["ticker"] for t in ticks] == ["NVDA", "AAPL"]
    assert ticks[0]["price"] == "180.42"
    assert ticks[0]["change_pct"] == 3.1
    assert ticks[0]["source"] == "alpaca"


@pytest.mark.asyncio
async def test_unknown_ticker_does_not_kill_stream(conn):
    ticks = [
        data
        async for _, data in quote_stream(["ZZZZ", "NVDA"], **_ctx(conn), interval=0, limit=1)
    ]
    assert [t["ticker"] for t in ticks] == ["NVDA"]  # bilinmeyen atlanır, akış sürer


def test_stream_quotes_endpoint_ends_with_done(conn, monkeypatch):
    # Why: /api/stream/quotes prod'da sınırsız akar (limit yok) — endpoint'i bounded
    # sürmek için quote_stream'i sahte, sonlu bir generator ile monkeypatch'liyoruz.
    async def _fake_quote_stream(tickers, **kwargs):
        yield events.QUOTE_TICK, {
            "ticker": "NVDA", "price": "1", "change_pct": 0.0, "source": "fake", "ts": 1,
        }

    monkeypatch.setattr(quotes_module, "quote_stream", _fake_quote_stream)

    reg = MarketRegistry()
    reg.register(FakeMarket())
    app = create_app(registry=reg, cache=Cache(conn))
    r = TestClient(app).get("/api/stream/quotes?tickers=NVDA")

    assert r.status_code == 200
    body = r.text
    assert "event: quote-tick" in body
    assert body.rstrip().endswith("event: done\ndata: {}")
