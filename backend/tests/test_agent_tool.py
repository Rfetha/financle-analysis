from sonar.agent.tools import make_quote_tool
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.market.us.prices import YFinancePrices
from sonar.store.cache import Cache


def _tool(conn):
    reg = MarketRegistry()
    reg.register(USMarketPlugin(YFinancePrices(now=lambda: 1.0, fetch=lambda t: (110.0, 100.0))))
    return make_quote_tool(registry=reg, cache=Cache(conn, now=lambda: 1.0), ttl=60)


def test_quote_tool_returns_computed_quote(conn):
    out = _tool(conn).invoke({"ticker": "AAPL"})
    assert out["ticker"] == "AAPL"
    assert out["change_pct"] == 10.0


def test_quote_tool_unknown_symbol_returns_error(conn):
    reg = MarketRegistry()

    def _bad(t):
        raise KeyError("exchangeTimezoneName")

    reg.register(USMarketPlugin(YFinancePrices(now=lambda: 1.0, fetch=_bad)))
    tool = make_quote_tool(registry=reg, cache=Cache(conn, now=lambda: 1.0), ttl=60)
    out = tool.invoke({"ticker": "ZZZZQ"})
    assert "error" in out
