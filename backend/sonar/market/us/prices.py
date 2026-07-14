"""Fiyat kaynağı = Strategy (GoF). Aynı interface, key'in varlığına göre değişen davranış.
Alpaca (resmî, sözleşmeli) Task A3'te eklenir; bu dosyada bugünkü yfinance yolu korunur.
"""

import time
from decimal import Decimal
from typing import Callable, Protocol

from sonar.domain.money import Money
from sonar.domain.quote import Provenance, Quote
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol


class PriceSource(Protocol):
    name: str

    def quote(self, symbol: Symbol) -> Quote: ...


def _yfinance_fetch(ticker: str) -> tuple[float, float]:
    import yfinance as yf

    fi = yf.Ticker(ticker).fast_info
    return float(fi.last_price), float(fi.previous_close)


class YFinancePrices:
    # Why: yfinance Yahoo'nun özel endpoint'ini kazır — resmî değil, kırılgan. Provenance'ta
    # bunu açıkça söylüyoruz ki kullanıcı hangi veriyle baktığını bilsin (spec §3).
    name = "yfinance (resmî değil)"

    def __init__(
        self,
        now: Callable[[], float] = time.time,
        fetch: Callable[[str], tuple[float, float]] = _yfinance_fetch,
    ) -> None:
        self._now = now
        self._fetch = fetch

    def quote(self, symbol: Symbol) -> Quote:
        try:
            last, prev = self._fetch(symbol.ticker)
        except (KeyError, TypeError) as e:
            # Why: yfinance bilinmeyen sembolde KeyError('exchangeTimezoneName')
            # (ya da None->float TypeError) fırlatır; temiz UnknownSymbol'e çevir.
            raise UnknownSymbol(symbol.ticker) from e
        return Quote(
            symbol=symbol,
            price=Money(Decimal(str(last)), "USD"),
            previous_close=Money(Decimal(str(prev)), "USD"),
            provenance=Provenance("yfinance", self._now()),
        )
