"""Short interest kaynağı. FINRA'nın key'siz consolidated short-interest dosyası
tutarsız/parse zor (spike B0 bulgusu) → robust fallback: yfinance `.info`
(`sharesShort`, `shortRatio`). Provenance bunu açıkça söyler (spec §3)."""

from typing import Callable

from sonar.domain.holdings import ShortInterest
from sonar.domain.symbol import Symbol


def _yf_info(ticker: str) -> dict:
    import yfinance as yf

    return yf.Ticker(ticker).info


class FinraShort:
    def __init__(self, fetch: Callable[[str], dict] = _yf_info) -> None:
        self._fetch = fetch

    def short_interest(self, symbol: Symbol) -> ShortInterest:
        info = self._fetch(symbol.ticker)
        return ShortInterest(
            symbol=symbol,
            shares_short=info.get("sharesShort") or 0,
            days_to_cover=info.get("shortRatio"),
            as_of="",
            source="Yahoo (ikinci-el)",
        )
