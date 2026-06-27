from dataclasses import dataclass
from sonar.domain.money import Money
from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str
    fetched_at: float


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: Symbol
    price: Money
    previous_close: Money
    provenance: Provenance

    @property
    def change_pct(self) -> float:
        prev = self.previous_close.amount
        if prev == 0:
            return 0.0
        return float((self.price.amount - prev) / prev * 100)
