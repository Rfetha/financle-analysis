from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_peers(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        return {
            "ticker": symbol.ticker,
            "peers": registry.get(symbol.market).get_peers(symbol),
            "source": "SEC EDGAR SIC",
        }

    return cached(cache, f"peers:{symbol.market}:{symbol.ticker}", ttl, compute)
