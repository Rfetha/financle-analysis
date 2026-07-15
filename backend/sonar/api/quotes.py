"""Canlı fiyat akışı. Çıktı sözleşmesi: quote-tick.

ponytail: polling. Alpaca WebSocket (Task A14) aynı quote-tick'i üretir → frontend farkı bilmez.
Cache TTL'i (60sn) polling aralığından uzun olduğu için cache'i BYPASS ediyoruz; canlı akışın
işi taze veri.
"""

import asyncio

from loguru import logger

from sonar.agent import events
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol, Unsupported
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache


async def quote_stream(
    tickers: list[str],
    *,
    registry: MarketRegistry,
    cache: Cache,
    interval: float = 15.0,
    limit: int | None = None,
    market: str = "US",
):
    loop = asyncio.get_running_loop()
    plugin = registry.get(market)
    rounds = 0
    while limit is None or rounds < limit:
        for ticker in tickers:
            symbol = Symbol(ticker, market)
            try:
                quote = await loop.run_in_executor(None, plugin.get_quote, symbol)
            except (UnknownSymbol, Unsupported) as e:
                logger.info("quote-stream: {} atlandı ({})", ticker, e)
                continue
            except Exception as e:  # noqa: BLE001 — tek sembolün hatası akışı düşürmesin
                logger.warning("quote-stream: {} hata ({})", ticker, e)
                continue
            yield events.QUOTE_TICK, {
                "ticker": symbol.ticker,
                "price": str(quote.price.amount),
                "change_pct": round(quote.change_pct, 2),
                "source": quote.provenance.source,
                "ts": quote.provenance.fetched_at,
            }
        rounds += 1
        if limit is None or rounds < limit:
            await asyncio.sleep(interval)
