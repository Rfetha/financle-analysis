"""Market sözleşmesi (ADR-0001/0005).

MarketPlugin = Protocol: yapısal sözleşme. Üçüncü-parti paket (sonar-market-tr) bize
bağlanmadan implement edebilsin diye nominal hiyerarşi dayatmıyoruz.

BaseMarketPlugin = opsiyonel ABC: tek işi *sözleşme bozunumu* — verilmeyen her yetenek
Unsupported fırlatır. Market yalnız verebildiğini override eder. (Protocol'de eksik metot
AttributeError'a düşer; bu ADR-0005'in açık cevabı değil.)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sonar.domain.quote import Quote
from sonar.domain.symbol import Symbol


class Unsupported(Exception):
    """Market bu yeteneği sağlayamıyor."""


class UnknownSymbol(Exception):
    """Market'te böyle bir sembol yok / veri bulunamadı."""


@runtime_checkable
class MarketPlugin(Protocol):
    market: str

    def get_quote(self, symbol: Symbol) -> Quote: ...
    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> "OhlcvSeries": ...
    def get_fundamentals(self, symbol: Symbol) -> "Fundamentals": ...
    def get_news(self, symbol: Symbol) -> list["NewsItem"]: ...
    def get_peers(self, symbol: Symbol) -> list[str]: ...
    def get_macro_snapshot(self) -> "MacroSnapshot": ...


class BaseMarketPlugin:
    """11 yeteneğin Unsupported varsayılanı."""

    market: str = "?"

    def get_quote(self, symbol: Symbol) -> Quote:
        raise Unsupported(f"{self.market}: quote")

    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> "OhlcvSeries":
        raise Unsupported(f"{self.market}: ohlcv")

    def get_fundamentals(self, symbol: Symbol) -> "Fundamentals":
        raise Unsupported(f"{self.market}: fundamentals")

    def get_news(self, symbol: Symbol) -> list["NewsItem"]:
        raise Unsupported(f"{self.market}: news")

    def get_peers(self, symbol: Symbol) -> list[str]:
        raise Unsupported(f"{self.market}: peers")

    def get_macro_snapshot(self) -> "MacroSnapshot":
        raise Unsupported(f"{self.market}: macro")

    def get_institutional_holders(self, symbol: Symbol):
        raise Unsupported(f"{self.market}: 13F")

    def get_insider_trades(self, symbol: Symbol):
        raise Unsupported(f"{self.market}: Form 4")

    def get_filer_holdings(self, filer_cik: str):
        raise Unsupported(f"{self.market}: 13F filer")

    def get_short_interest(self, symbol: Symbol):
        raise Unsupported(f"{self.market}: short interest")
