from dataclasses import asdict

from sonar.analytics.insiders import cluster
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached

NOTE = "Form 4 · 2 iş günü gecikmeli · yalnız açık piyasa alım/satımı (hibe/vergi hariç)."


def get_insider_trades(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        trades = registry.get(symbol.market).get_insider_trades(symbol)
        return {
            "ticker": symbol.ticker,
            "trades": [asdict(t) for t in trades],
            "cluster": cluster(trades),
            "provenance_note": NOTE,
        }

    return cached(cache, f"insiders:{symbol.market}:{symbol.ticker}", ttl, compute)
