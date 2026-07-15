"""US'a özel makro. FRED'in aynı istemcisini kullanır; seri seçimi market bilgisidir."""

from datetime import date

from sonar.domain.macro import LocalSnapshot
from sonar.market.sources.fred import FredClient

FED_FUNDS = "FEDFUNDS"
CPI = "CPIAUCSL"
Y10 = "DGS10"
Y2 = "DGS2"

CPI_YOY_WINDOW_DAYS = 62  # ~2 ay tolerans — bunun dışı "yıllık" olarak yanıltıcı


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
        """TÜFE endeksi → yıllık % değişim. FRED endeks verir, yüzde değil (bu hesap bizim işimiz).

        Why: yıl-öncesi tam eşleşme yoksa en yakın gözlem kullanılır, ama ±2 ay
        penceresinin dışındaki bir gözlemle "yıllık" hesap yanıltıcı olur — bu
        durumda None dönülür (eski kod en eski gözleme düşüyordu, çok yıllı
        aralıkta yanlış YoY üretiyordu).
        """
        if len(cpi) < 2:
            return None
        latest_date, latest_val = cpi[-1]
        latest_dt = date.fromisoformat(latest_date)
        try:
            target = latest_dt.replace(year=latest_dt.year - 1)
        except ValueError:  # 29 Şubat
            target = latest_dt.replace(year=latest_dt.year - 1, day=28)
        closest_date, closest_val = min(
            cpi[:-1], key=lambda dv: abs((date.fromisoformat(dv[0]) - target).days)
        )
        if abs((date.fromisoformat(closest_date) - target).days) > CPI_YOY_WINDOW_DAYS:
            return None
        if not closest_val:
            return None
        return round((latest_val - closest_val) / closest_val * 100, 2)
