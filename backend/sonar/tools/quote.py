import json
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache


def get_quote(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)
    key = f"quote:{symbol.market}:{symbol.ticker}"
    cached = cache.get(key)
    if cached is not None:
        return json.loads(cached)

    quote = registry.get(symbol.market).get_quote(symbol)
    out = {
        "ticker": symbol.ticker,
        "price": str(quote.price.amount),
        "currency": quote.price.currency,
        "change_pct": round(quote.change_pct, 2),
        "source": quote.provenance.source,
    }
    cache.set(key, json.dumps(out), ttl)
    return out
