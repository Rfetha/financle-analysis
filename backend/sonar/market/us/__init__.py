"""US market plugin — ince composer. Yetenekleri kaynaklara dağıtır, domain VO'ya çevirir.
Hangi kaynağın hangi yeteneği doldurduğu buranın bilgisi; tool yüzeyine sızmaz.

Kompozisyon (Template Method YOK, spec §4): makro = global + yerel iki kaynağın birleşimi;
her ikisi de enjekte edilir, miras alınmaz.
"""

import os
import time

from sonar.domain.candle import OhlcvSeries
from sonar.domain.fundamentals import Fundamentals
from sonar.domain.macro import MacroSnapshot
from sonar.domain.news import NewsItem
from sonar.domain.quote import Provenance, Quote
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.sources.fred import FredClient
from sonar.market.sources.global_macro import GlobalMacro
from sonar.market.sources.http import HttpClient
from sonar.market.us.edgar import EdgarClient
from sonar.market.us.macro import USMacro
from sonar.market.us.news import USNews
from sonar.market.us.finra import FinraShort
from sonar.market.us.prices import PriceSource, YFinancePrices


def _default_http() -> HttpClient:
    """SEC/FRED nezaketi: gerçek iletişim adresi içeren User-Agent (SONAR_CONTACT ile override)."""
    contact = os.environ.get("SONAR_CONTACT", "sonar@localhost")
    return HttpClient(f"Sonar/0.1 ({contact})")


class USMarketPlugin(BaseMarketPlugin):
    market = "US"

    def __init__(
        self,
        prices: PriceSource | None = None,
        edgar: EdgarClient | None = None,
        news: USNews | None = None,
        global_macro: GlobalMacro | None = None,
        local_macro: USMacro | None = None,
        finra: FinraShort | None = None,
    ) -> None:
        http = _default_http()
        fred = FredClient(http)
        self._prices = prices or YFinancePrices()
        self._edgar = edgar or EdgarClient(http)
        self._news = news or USNews(http)
        self._global = global_macro or GlobalMacro(fred)
        self._local = local_macro or USMacro(fred)
        self._finra = finra or FinraShort()

    def get_quote(self, symbol: Symbol) -> Quote:
        return self._prices.quote(symbol)

    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        return self._prices.bars(symbol, range_, interval)

    def get_fundamentals(self, symbol: Symbol) -> Fundamentals:
        return self._edgar.fundamentals(symbol)

    def get_news(self, symbol: Symbol) -> list[NewsItem]:
        return self._news.for_symbol(symbol)

    def get_peers(self, symbol: Symbol) -> list[str]:
        return self._edgar.peers(symbol)

    def get_macro_snapshot(self) -> MacroSnapshot:
        return MacroSnapshot(
            global_=self._global.snapshot(),
            local=self._local.snapshot(),
            provenance=Provenance("FRED", time.time()),
        )

    def get_insider_trades(self, symbol: Symbol):
        return self._edgar.insider_trades(symbol)

    def get_short_interest(self, symbol: Symbol):
        return self._finra.short_interest(symbol)
