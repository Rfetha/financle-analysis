import httpx
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.us.prices import AlpacaPrices, YFinancePrices, make_price_source

SNAPSHOT = {
    "latestTrade": {"p": 180.42},
    "prevDailyBar": {"c": 175.00},
}


def _alpaca(monkeypatch=None):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=SNAPSHOT))
    http = HttpClient("Sonar/0.1 (t@e.com)", transport=transport, min_interval=0)
    return AlpacaPrices(key="k", secret="s", http=http, now=lambda: 7.0)


def test_alpaca_quote_uses_snapshot():
    q = _alpaca().quote(Symbol("NVDA", "US"))
    assert str(q.price.amount) == "180.42"
    assert str(q.previous_close.amount) == "175.0"
    assert q.provenance.source == "alpaca"
    assert round(q.change_pct, 2) == 3.1


def test_make_price_source_without_key_falls_back_to_yfinance(monkeypatch):
    monkeypatch.delenv("SONAR_ALPACA_KEY", raising=False)
    assert isinstance(make_price_source(), YFinancePrices)


def test_make_price_source_with_key_uses_alpaca(monkeypatch):
    monkeypatch.setenv("SONAR_ALPACA_KEY", "k")
    monkeypatch.setenv("SONAR_ALPACA_SECRET", "s")
    assert isinstance(make_price_source(), AlpacaPrices)


import os
import pytest


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("SONAR_ALPACA_KEY"), reason="Alpaca key yok")
def test_alpaca_real_quote():
    src = AlpacaPrices(
        key=os.environ["SONAR_ALPACA_KEY"], secret=os.environ["SONAR_ALPACA_SECRET"]
    )
    q = src.quote(Symbol("AAPL", "US"))
    assert q.price.amount > 0
