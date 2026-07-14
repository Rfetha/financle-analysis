from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.technicals import get_technicals


def _candles(n=60):
    return [
        Candle(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
        for i in range(n)
    ]


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        return OhlcvSeries(symbol, interval, _candles(), Provenance("fake", 1.0))


def _reg():
    reg = MarketRegistry()
    reg.register(FakeMarket())
    return reg


def test_technicals_returns_computed_indicators(conn):
    out = get_technicals("nvda", registry=_reg(), cache=Cache(conn), ttl=900)
    assert out["ticker"] == "NVDA"
    assert out["rsi"] == 100.0            # sürekli yükselen seri
    assert out["macd"]["macd"] > 0
    assert out["support"] < out["resistance"]
    assert out["volume_anomaly"] == 1.0   # sabit hacim
    assert "obv" in out and "bollinger" in out and "ema50" in out
