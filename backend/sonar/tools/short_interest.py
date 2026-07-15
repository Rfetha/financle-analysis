from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached

NOTE = (
    "Short interest · TOPLAM rakam — kimin short'ladığı bilinmiyor "
    "(kurumsal short ABD'de bildirilmiyor)."
)


def get_short_interest(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        si = registry.get(symbol.market).get_short_interest(symbol)
        return {
            "ticker": symbol.ticker,
            "shares_short": si.shares_short,
            "days_to_cover": si.days_to_cover,
            "source": si.source,
            "provenance_note": NOTE,
        }

    return cached(cache, f"short_interest:{symbol.market}:{symbol.ticker}", ttl, compute)
