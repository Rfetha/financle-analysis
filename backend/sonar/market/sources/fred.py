"""FRED — key'siz CSV endpoint'i. (Resmî API key ister; grafik CSV'si istemez → key yok.)"""

import csv as csv_module

from sonar.market.sources.http import HttpClient

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={ids}"


class FredClient:
    source = "FRED"

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def series(self, series_id: str) -> list[tuple[str, float]]:
        """Tek seri, (observation_date, value) listesi (eski→yeni).

        Why: `?id=` birden fazla seri alırsa FRED ZIP döner (CSV değil) — CSV
        olarak parse edince her değer sessizce None oluyordu (canlı FRED'e karşı
        yakalanan bug). Bu yüzden istek başına tek id.
        """
        text = self._http.get_text(FRED_CSV.format(ids=series_id))
        # Why: gerçek FRED CSV'si CRLF/karışık satır sonu döndürüyor; StringIO'ya ham verince
        # csv "new-line in unquoted field" ile patlıyor. splitlines() satır sonlarını normalize
        # eder → csv temiz satır listesi alır.
        rows = csv_module.DictReader(text.splitlines())
        out: list[tuple[str, float]] = []
        for row in rows:
            raw = (row.get(series_id) or "").strip()
            if raw and raw != ".":
                out.append((row["observation_date"], float(raw)))
        return out

    def latest(self, series_ids: list[str]) -> dict[str, float]:
        """Her seri için en son *dolu* değer. FRED eksik günü '.' ile yazar."""
        out: dict[str, float] = {}
        for sid in series_ids:
            values = self.series(sid)
            if values:
                out[sid] = values[-1][1]
        return out
