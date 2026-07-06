"""Deep tool'ların ReAct'e (@tool) açılan yüzeyi. Hesaplama çekirdekte (ADR-0003),
tool yalnız yapılandırılmış sonucu döner; LLM aritmetik yapmaz."""

from langchain_core.tools import tool

from sonar.market.base import UnknownSymbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.quote import get_quote


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
