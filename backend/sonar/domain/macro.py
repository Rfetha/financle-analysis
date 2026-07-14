from dataclasses import dataclass

from sonar.domain.quote import Provenance


@dataclass(frozen=True, slots=True)
class GlobalSnapshot:
    """Ülkeden bağımsız rejim: oynaklık, dolar, emtia. Her market kullanır."""
    vix: float | None
    dxy: float | None
    wti: float | None


@dataclass(frozen=True, slots=True)
class LocalSnapshot:
    """Market'in ülkesine özel: politika faizi, enflasyon, getiri eğrisi."""
    fed_funds: float | None
    cpi_yoy: float | None
    yield_10y: float | None
    yield_2y: float | None
    curve_10y_2y: float | None


@dataclass(frozen=True, slots=True)
class MacroSnapshot:
    global_: GlobalSnapshot
    local: LocalSnapshot
    provenance: Provenance
