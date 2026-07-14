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
        rows = self._fred.history([FED_FUNDS, CPI, Y10, Y2])
        latest = self._fred.latest([FED_FUNDS, CPI, Y10, Y2])
        y10, y2 = latest.get(Y10), latest.get(Y2)
        return LocalSnapshot(
            fed_funds=latest.get(FED_FUNDS),
            cpi_yoy=self._cpi_yoy(rows),
            yield_10y=y10,
            yield_2y=y2,
            curve_10y_2y=round(y10 - y2, 2) if y10 is not None and y2 is not None else None,
        )

    def _cpi_yoy(self, rows: list[dict[str, str]]) -> float | None:
        """TÜFE endeksi → yıllık % değişim. FRED endeks verir, yüzde değil (bu hesap bizim işimiz)."""
        values = [
            (row["DATE"], float(row[CPI]))
            for row in rows
            if (row.get(CPI) or "").strip() not in ("", ".")
        ]
        if len(values) < 2:
            return None
        latest_date, latest_val = values[-1]
        year_ago = latest_date[:4] and str(int(latest_date[:4]) - 1) + latest_date[4:]
        prior = next((v for d, v in values if d == year_ago), values[0][1])
        if not prior:
            return None
        return round((latest_val - prior) / prior * 100, 2)
