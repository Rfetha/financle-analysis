from dataclasses import asdict

from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_macro_snapshot(
    *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    def compute() -> dict:
        snap = registry.get(market).get_macro_snapshot()
        return {
            "global": asdict(snap.global_),
            "local": asdict(snap.local),
            "source": snap.provenance.source,
        }

    return cached(cache, f"macro:{market}", ttl, compute)
