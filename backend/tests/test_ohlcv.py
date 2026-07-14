from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.ohlcv import get_ohlcv

CANDLES = [
    Candle(ts=1, open=10.0, high=11.0, low=9.0, close=10.5, volume=1000),
    Candle(ts=2, open=10.5, high=12.0, low=10.0, close=11.5, volume=2000),
]


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def __init__(self):
        self.calls = 0

    def get_ohlcv(self, symbol, range_, interval):
        self.calls += 1
        return OhlcvSeries(
            symbol=symbol, interval=interval, candles=CANDLES,
            provenance=Provenance("fake", 1.0),
        )


def _reg(plugin):
    reg = MarketRegistry()
    reg.register(plugin)
    return reg


def test_get_ohlcv_returns_serialisable_candles(conn):
    out = get_ohlcv("nvda", "6mo", "1d", registry=_reg(FakeMarket()), cache=Cache(conn), ttl=60)
    assert out["ticker"] == "NVDA"
    assert out["source"] == "fake"
    assert out["candles"][1] == {
        "ts": 2, "open": 10.5, "high": 12.0, "low": 10.0, "close": 11.5, "volume": 2000
    }


def test_get_ohlcv_second_call_hits_cache(conn):
    plugin = FakeMarket()
    cache = Cache(conn, now=lambda: 1.0)
    get_ohlcv("NVDA", "6mo", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    get_ohlcv("NVDA", "6mo", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    assert plugin.calls == 1


def test_cache_key_varies_by_range(conn):
    plugin = FakeMarket()
    cache = Cache(conn, now=lambda: 1.0)
    get_ohlcv("NVDA", "6mo", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    get_ohlcv("NVDA", "1y", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    assert plugin.calls == 2  # farklı range = farklı cache anahtarı
