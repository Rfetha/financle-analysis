"""Deep tool'ların ReAct'e (@tool) açılan yüzeyi. Hesaplama çekirdekte (ADR-0003),
tool yalnız yapılandırılmış sonucu döner; LLM aritmetik yapmaz."""

from langchain_core.tools import tool

from sonar import config
from sonar.market.base import UnknownSymbol, Unsupported
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.fundamentals import get_fundamentals
from sonar.tools.macro import get_macro_snapshot
from sonar.tools.news import get_news
from sonar.tools.ohlcv import get_ohlcv
from sonar.tools.peers import get_peers
from sonar.tools.quote import get_quote
from sonar.tools.technicals import get_technicals


def make_quote_tool(*, registry: MarketRegistry, cache: Cache, ttl: int):
    @tool
    def get_stock_quote(ticker: str) -> dict:
        """Bir ABD hissesinin güncel fiyatını, günlük % değişimini ve kaynağını döner.
        ticker: hisse sembolü (ör. AAPL, NVDA)."""
        try:
            return get_quote(ticker, registry=registry, cache=cache, ttl=ttl)
        except UnknownSymbol:
            return {"error": f"Bilinmeyen sembol: {ticker.upper()}"}

    return get_stock_quote


def make_tools(*, registry: MarketRegistry, cache: Cache) -> list:
    """7 deep tool: ADR-0007 — recipe'yle aynı `sonar.tools.*` çağrıları, @tool sarmalı."""
    ctx = {"registry": registry, "cache": cache}

    def guard(fn):
        """Tool hataları LLM'e okunur mesaj olarak döner — akış çökmez, sayı uydurulmaz."""
        try:
            return fn()
        except UnknownSymbol as e:
            return {"error": f"Bilinmeyen sembol: {e}"}
        except Unsupported as e:
            return {"error": f"Bu market bunu vermiyor: {e}"}

    @tool
    def get_price_history(ticker: str, range: str = "6mo", interval: str = "1d") -> dict:
        """Hissenin fiyat serisini (mum) döner. range: 1mo|3mo|6mo|1y|2y|5y, interval: 1d|1h|5m."""
        return guard(
            lambda: get_ohlcv(ticker, range, interval, **ctx, ttl=config.OHLCV_TTL_SECONDS)
        )

    @tool
    def get_technical_indicators(ticker: str) -> dict:
        """RSI, MACD, Bollinger, EMA50/200, destek-direnç, OBV, hacim anomalisi — HESAPLANMIŞ döner."""
        return guard(lambda: get_technicals(ticker, **ctx, ttl=config.OHLCV_TTL_SECONDS))

    @tool
    def get_company_fundamentals(ticker: str) -> dict:
        """SEC EDGAR'dan gelir, net kâr, marj, yıllık büyüme (resmî XBRL beyanı)."""
        return guard(
            lambda: get_fundamentals(ticker, **ctx, ttl=config.FUNDAMENTALS_TTL_SECONDS)
        )

    @tool
    def get_stock_news(ticker: str) -> dict:
        """Hisseyle ilgili son haber başlıkları (kaynak + zaman ile)."""
        return guard(lambda: get_news(ticker, **ctx, ttl=config.NEWS_TTL_SECONDS))

    @tool
    def get_macro_snapshot_tool() -> dict:
        """Makro pano: politika faizi, TÜFE, 10Y/2Y getiri, eğri, VIX, dolar endeksi, petrol."""
        return guard(lambda: get_macro_snapshot(**ctx, ttl=config.MACRO_TTL_SECONDS))

    @tool
    def get_sector_peers(ticker: str) -> dict:
        """Aynı sektördeki (SEC SIC kodu) rakip şirketler."""
        return guard(lambda: get_peers(ticker, **ctx, ttl=config.PEERS_TTL_SECONDS))

    get_macro_snapshot_tool.name = "get_macro_snapshot"

    return [
        make_quote_tool(registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS),
        get_price_history,
        get_technical_indicators,
        get_company_fundamentals,
        get_stock_news,
        get_macro_snapshot_tool,
        get_sector_peers,
    ]
