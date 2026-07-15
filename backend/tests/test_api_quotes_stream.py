import pytest
from sonar.api.quotes import quote_stream
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
