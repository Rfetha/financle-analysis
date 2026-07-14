"""Teknik gösterge tool'u — market plugin'ine DOKUNMAZ.
OHLCV'yi tool katmanından alır, hesabı analytics'te yapar (ADR-0003: sayı çekirdekte).
"""

from sonar.analytics import indicators
from sonar.domain.candle import Candle
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached
from sonar.tools.ohlcv import get_ohlcv


def get_technicals(
    ticker: str,
    *,
    registry: MarketRegistry,
    cache: Cache,
    ttl: int,
    market: str = "US",
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        raw = get_ohlcv(
            symbol.ticker, "1y", "1d",
            registry=registry, cache=cache, ttl=ttl, market=market,
        )
        candles = [Candle(**c) for c in raw["candles"]]
        closes = [c.close for c in candles]
        sr = indicators.support_resistance(candles)
        return {
            "ticker": symbol.ticker,
            "rsi": round(indicators.rsi(closes), 2),
            "macd": indicators.macd(closes),
            "bollinger": indicators.bollinger(closes),
            "ema50": round(indicators.ema(closes, 50), 2),
            "ema200": round(indicators.ema(closes, 200), 2) if len(closes) >= 200 else None,
            "support": sr["support"],
            "resistance": sr["resistance"],
            "obv": indicators.obv(candles),
            "volume_anomaly": indicators.volume_anomaly(candles),
            "source": raw["source"],
        }

    return cached(cache, f"technicals:{symbol.market}:{symbol.ticker}", ttl, compute)
