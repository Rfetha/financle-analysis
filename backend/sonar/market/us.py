import time
from decimal import Decimal
from typing import Callable
from sonar.domain.symbol import Symbol
from sonar.domain.money import Money
from sonar.domain.quote import Quote, Provenance


def _yfinance_fetch(ticker: str) -> tuple[float, float]:
    import yfinance as yf
    fi = yf.Ticker(ticker).fast_info
    return float(fi.last_price), float(fi.previous_close)


class USMarketPlugin:
    market = "US"

    def __init__(
        self,
        now: Callable[[], float] = time.time,
        fetch: Callable[[str], tuple[float, float]] = _yfinance_fetch,
    ) -> None:
        self._now = now
        self._fetch = fetch

    def get_quote(self, symbol: Symbol) -> Quote:
        last, prev = self._fetch(symbol.ticker)
        return Quote(
            symbol=symbol,
            price=Money(Decimal(str(last)), "USD"),
            previous_close=Money(Decimal(str(prev)), "USD"),
            provenance=Provenance("yfinance", self._now()),
        )
