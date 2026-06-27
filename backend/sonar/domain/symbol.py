from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    ticker: str
    market: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", self.ticker.upper())
