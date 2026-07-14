from dataclasses import asdict

from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_news(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        items = registry.get(symbol.market).get_news(symbol)
        return {"ticker": symbol.ticker, "items": [asdict(i) for i in items]}

    return cached(cache, f"news:{symbol.market}:{symbol.ticker}", ttl, compute)
