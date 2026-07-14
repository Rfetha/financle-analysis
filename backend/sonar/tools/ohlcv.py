from dataclasses import asdict

from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_ohlcv(
    ticker: str,
    range_: str = "6mo",
    interval: str = "1d",
    *,
    registry: MarketRegistry,
    cache: Cache,
    ttl: int,
    market: str = "US",
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        series = registry.get(symbol.market).get_ohlcv(symbol, range_, interval)
        return {
            "ticker": symbol.ticker,
            "interval": series.interval,
            "candles": [asdict(c) for c in series.candles],
            "source": series.provenance.source,
        }

    return cached(cache, f"ohlcv:{symbol.market}:{symbol.ticker}:{range_}:{interval}", ttl, compute)
