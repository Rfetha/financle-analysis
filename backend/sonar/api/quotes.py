"""Canlı fiyat akışı. Çıktı sözleşmesi: quote-tick.

ponytail: polling. Alpaca WebSocket (Task A14) aynı quote-tick'i üretir → frontend farkı bilmez.
Cache TTL'i (60sn) polling aralığından uzun olduğu için cache'i BYPASS ediyoruz; canlı akışın
işi taze veri.
"""

import asyncio
import os

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

    key, secret = os.environ.get("SONAR_ALPACA_KEY"), os.environ.get("SONAR_ALPACA_SECRET")
    if key and secret and limit is None:
        # Why: WS gerçek push verir; polling yalnız key yokken (yfinance) ya da testte (limit) kullanılır.
        from sonar.market.us.stream import AlpacaStream

        prev_closes: dict[str, float] = {}
        async for tick in AlpacaStream(key, secret).ticks([t.upper() for t in tickers]):
            ticker = tick["ticker"]
            try:
                if ticker not in prev_closes:
                    q = await loop.run_in_executor(None, plugin.get_quote, Symbol(ticker, market))
                    prev_closes[ticker] = float(q.previous_close.amount)
                prev = prev_closes[ticker]
                change = (float(tick["price"]) - prev) / prev * 100 if prev else 0.0
            except (UnknownSymbol, Unsupported) as e:
                logger.info("quote-stream(ws): {} atlandı ({})", ticker, e)
                continue
            except Exception as e:  # noqa: BLE001 — tek tick'in hatası akışı düşürmesin
                logger.warning("quote-stream(ws): {} hata ({})", ticker, e)
                continue
            yield events.QUOTE_TICK, {**tick, "change_pct": round(change, 2), "source": "alpaca"}
        return

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
