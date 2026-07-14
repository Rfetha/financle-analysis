from dataclasses import dataclass

from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Candle:
    ts: int          # unix saniye, bar açılışı
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class OhlcvSeries:
    symbol: Symbol
    interval: str    # "1d" | "1h" | "5m"
    candles: list[Candle]
    provenance: Provenance
