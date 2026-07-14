from dataclasses import asdict

from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_fundamentals(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        f = registry.get(symbol.market).get_fundamentals(symbol)
        out = asdict(f)
        out["ticker"] = symbol.ticker
        out["source"] = f.provenance.source
        out.pop("symbol")
        out.pop("provenance")
        return out

    return cached(cache, f"fundamentals:{symbol.market}:{symbol.ticker}", ttl, compute)
