"""US'a özel makro. FRED'in aynı istemcisini kullanır; seri seçimi market bilgisidir."""

from sonar.domain.macro import LocalSnapshot
from sonar.market.sources.fred import FredClient

FED_FUNDS = "FEDFUNDS"
CPI = "CPIAUCSL"
Y10 = "DGS10"
Y2 = "DGS2"


class USMacro:
    def __init__(self, fred: FredClient) -> None:
        self._fred = fred

    def snapshot(self) -> LocalSnapshot:
        latest = self._fred.latest([FED_FUNDS, Y10, Y2])
        cpi = self._fred.series(CPI)
        y10, y2 = latest.get(Y10), latest.get(Y2)
        return LocalSnapshot(
            fed_funds=latest.get(FED_FUNDS),
            cpi_yoy=self._cpi_yoy(cpi),
            yield_10y=y10,
            yield_2y=y2,
            curve_10y_2y=round(y10 - y2, 2) if y10 is not None and y2 is not None else None,
        )

    def _cpi_yoy(self, cpi: list[tuple[str, float]]) -> float | None:
        """TÜFE endeksi → yıllık % değişim. FRED endeks verir, yüzde değil (bu hesap bizim işimiz)."""
        if len(cpi) < 2:
            return None
        latest_date, latest_val = cpi[-1]
        year_ago = str(int(latest_date[:4]) - 1) + latest_date[4:]
        prior = next((v for d, v in cpi if d == year_ago), cpi[0][1])
        if not prior:
            return None
        return round((latest_val - prior) / prior * 100, 2)
