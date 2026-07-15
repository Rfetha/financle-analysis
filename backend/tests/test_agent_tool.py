from sonar.agent.tools import make_quote_tool, make_tools
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
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


def test_make_tools_exposes_ten_deep_tools(conn):
    reg = MarketRegistry()
    reg.register(USMarketPlugin())
    names = {t.name for t in make_tools(registry=reg, cache=Cache(conn), conn=conn)}
    assert names == {
        "get_stock_quote", "get_price_history", "get_technical_indicators",
        "get_company_fundamentals", "get_stock_news", "get_macro_snapshot", "get_sector_peers",
        "get_institutional_holders", "get_insider_trades", "get_short_interest",
    }


class TooShortMarket(BaseMarketPlugin):
    """RSI için 15 mum gerekir — 5 döner, analytics.indicators ValueError fırlatır."""

    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        candles = [
            Candle(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
            for i in range(5)
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("fake", 1.0))


def test_technical_indicators_tool_returns_error_dict_on_insufficient_data(conn):
    reg = MarketRegistry()
    reg.register(TooShortMarket())
    tools = {t.name: t for t in make_tools(registry=reg, cache=Cache(conn))}
    out = tools["get_technical_indicators"].invoke({"ticker": "NVDA"})
    assert "error" in out
