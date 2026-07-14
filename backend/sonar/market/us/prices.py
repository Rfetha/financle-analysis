"""Fiyat kaynağı = Strategy (GoF). Aynı interface, key'in varlığına göre değişen davranış.
Alpaca (resmî, sözleşmeli) Task A3'te eklenir; bu dosyada bugünkü yfinance yolu korunur.
"""

import os
import time
from decimal import Decimal
from typing import Callable, Protocol

import httpx

from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.money import Money
from sonar.domain.quote import Provenance, Quote
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol
from sonar.market.sources.http import HttpClient

ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks"


class PriceSource(Protocol):
    name: str

    def quote(self, symbol: Symbol) -> Quote: ...
    def bars(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries: ...


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

    def bars(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        import yfinance as yf

        df = yf.Ticker(symbol.ticker).history(period=range_, interval=interval)
        if df.empty:
            raise UnknownSymbol(symbol.ticker)
        candles = [
            Candle(
                ts=int(idx.timestamp()),
                open=float(row.Open), high=float(row.High), low=float(row.Low),
                close=float(row.Close), volume=int(row.Volume),
            )
            for idx, row in df.iterrows()
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("yfinance", self._now()))


class AlpacaPrices:
    """Resmî, sözleşmeli fiyat API'si. Tek snapshot çağrısı = son işlem + önceki günün kapanışı."""

    name = "alpaca"

    _TIMEFRAME = {"1d": "1Day", "1h": "1Hour", "5m": "5Min"}
    _RANGE_DAYS = {"1mo": 31, "3mo": 93, "6mo": 186, "1y": 366, "2y": 731, "5y": 1827}

    def __init__(
        self,
        *,
        key: str,
        secret: str,
        http: HttpClient | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._now = now
        self._http = http or HttpClient(
            f"Sonar/0.1 ({os.environ.get('SONAR_CONTACT', 'sonar@localhost')})",
            min_interval=0.3,  # Alpaca ücretsiz katman: 200 req/dk
            extra_headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
        )

    def quote(self, symbol: Symbol) -> Quote:
        try:
            data = self._http.get_json(f"{ALPACA_DATA_URL}/{symbol.ticker}/snapshot")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                raise UnknownSymbol(symbol.ticker) from e
            raise
        trade = data.get("latestTrade") or {}
        prev = data.get("prevDailyBar") or {}
        if "p" not in trade or "c" not in prev:
            raise UnknownSymbol(symbol.ticker)
        return Quote(
            symbol=symbol,
            price=Money(Decimal(str(trade["p"])), "USD"),
            previous_close=Money(Decimal(str(prev["c"])), "USD"),
            provenance=Provenance("alpaca", self._now()),
        )

    def bars(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        from datetime import datetime, timedelta, timezone

        tf = self._TIMEFRAME.get(interval)
        days = self._RANGE_DAYS.get(range_)
        if tf is None or days is None:
            raise ValueError(f"desteklenmeyen range/interval: {range_}/{interval}")
        start = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        url = (
            f"{ALPACA_DATA_URL}/{symbol.ticker}/bars"
            f"?timeframe={tf}&start={start}&limit=10000&adjustment=split"
        )
        try:
            data = self._http.get_json(url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                raise UnknownSymbol(symbol.ticker) from e
            raise
        bars = data.get("bars") or []
        if not bars:
            raise UnknownSymbol(symbol.ticker)
        candles = [
            Candle(
                ts=int(datetime.fromisoformat(b["t"].replace("Z", "+00:00")).timestamp()),
                open=float(b["o"]), high=float(b["h"]), low=float(b["l"]), close=float(b["c"]),
                volume=int(b["v"]),
            )
            for b in bars
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("alpaca", self._now()))


def make_price_source() -> PriceSource:
    """Strategy seçimi: key varsa Alpaca (resmî), yoksa yfinance (kırılgan, Provenance söyler)."""
    key = os.environ.get("SONAR_ALPACA_KEY")
    secret = os.environ.get("SONAR_ALPACA_SECRET")
    if key and secret:
        return AlpacaPrices(key=key, secret=secret)
    return YFinancePrices()
