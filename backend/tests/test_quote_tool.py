from decimal import Decimal
from sonar.tools.quote import get_quote
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.market.us.prices import YFinancePrices
from sonar.store.cache import Cache


def _registry():
    reg = MarketRegistry()
    reg.register(USMarketPlugin(YFinancePrices(now=lambda: 1.0, fetch=lambda t: (110.0, 100.0))))
    return reg


def test_get_quote_returns_computed_dict(conn):
    out = get_quote("aapl", registry=_registry(), cache=Cache(conn), ttl=60)
    assert out["ticker"] == "AAPL"
    assert out["price"] == "110.0"
    assert out["change_pct"] == 10.0
    assert out["currency"] == "USD"
    assert out["source"] == "yfinance"


def test_get_quote_second_call_hits_cache(conn):
    calls = {"n": 0}
    def fetch(t):
        calls["n"] += 1
        return (110.0, 100.0)
    reg = MarketRegistry()
    reg.register(USMarketPlugin(YFinancePrices(now=lambda: 1.0, fetch=fetch)))
    cache = Cache(conn, now=lambda: 1.0)
    get_quote("AAPL", registry=reg, cache=cache, ttl=60)
    get_quote("AAPL", registry=reg, cache=cache, ttl=60)
    assert calls["n"] == 1  # ikinci çağrı cache'ten
