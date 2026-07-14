from dataclasses import dataclass

from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Fundamentals:
    symbol: Symbol
    period: str                       # "FY2026"
    revenue: float | None
    net_income: float | None
    net_margin: float | None          # %
    revenue_growth_yoy: float | None  # %
    provenance: Provenance
