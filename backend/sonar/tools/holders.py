"""Big Players tool'ları.

Her çıktı DÜRÜSTLÜK NOTU taşır (spec §7): 13F 45 gün gecikmeli, yalnız long ABD hissesi + listed
opsiyon. Short ve swap ABD'de bildirilmiyor (Archegos boşluğu) — bu bir eksiklik değil, verinin sınırı.
Not dipnot değil, tool çıktısının parçası: LLM sentezinde de görünsün.
"""

import sqlite3

from sonar.analytics.holdings import delta_report
from sonar.market.us.cusip import CusipMap
from sonar.store.cache import Cache
from sonar.store.holdings_repo import HoldingsRepo
from sonar.tools._cache import cached

NOTE = (
    "13F · {quarter} · 45 gün gecikmeli · yalnız long ABD hissesi + listed opsiyon. "
    "Short ve swap görünmez — bu bir eksiklik değil, verinin sınırı."
)


def get_institutional_holders(
    ticker: str, *, conn: sqlite3.Connection, cache: Cache, ttl: int, top: int = 10
) -> dict:
    def compute() -> dict:
        cusip = CusipMap(conn).cusip_for(ticker)
        if cusip is None:
            return {"unavailable": f"{ticker.upper()}: CUSIP haritada yok (13F eşleşmedi)"}
        repo = HoldingsRepo(conn)
        quarters = repo.quarters()
        if not quarters:
            return {"unavailable": "13F verisi henüz indirilmedi (/api/ingest/status)"}

        current = quarters[-1]
        previous = quarters[-2] if len(quarters) > 1 else None
        report = delta_report(
            repo.holders_of(cusip, previous) if previous else [],
            repo.holders_of(cusip, current),
            top=top,
        )
        return {
            "ticker": ticker.upper(),
            "quarter": current,
            "compared_to": previous,
            **report,
            "trend": repo.trend(cusip),
            "provenance_note": NOTE.format(quarter=current),
        }

    return cached(cache, f"holders:{ticker.upper()}", ttl, compute)


def get_filer_holdings(
    filer_cik: str, *, conn: sqlite3.Connection, cache: Cache, ttl: int
) -> dict:
    def compute() -> dict:
        repo = HoldingsRepo(conn)
        quarters = repo.quarters()
        if not quarters:
            return {"unavailable": "13F verisi henüz indirilmedi"}
        current = quarters[-1]
        return {
            "filer_cik": filer_cik,
            "quarter": current,
            "positions": repo.filer_holdings(filer_cik, current),
            "provenance_note": NOTE.format(quarter=current),
        }

    return cached(cache, f"filer:{filer_cik}", ttl, compute)
