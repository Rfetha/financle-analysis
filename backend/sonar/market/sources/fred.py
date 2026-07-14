"""FRED — key'siz CSV endpoint'i. (Resmî API key ister; grafik CSV'si istemez → key yok.)"""

import csv as csv_module
import io

from sonar.market.sources.http import HttpClient

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={ids}"


class FredClient:
    source = "FRED"

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def history(self, series_ids: list[str]) -> list[dict[str, str]]:
        text = self._http.get_text(FRED_CSV.format(ids=",".join(series_ids)))
        return list(csv_module.DictReader(io.StringIO(text)))

    def latest(self, series_ids: list[str]) -> dict[str, float]:
        """Her seri için en son *dolu* değer. FRED eksik günü '.' ile yazar."""
        out: dict[str, float] = {}
        for row in self.history(series_ids):
            for sid in series_ids:
                raw = (row.get(sid) or "").strip()
                if raw and raw != ".":
                    out[sid] = float(raw)
        return out
