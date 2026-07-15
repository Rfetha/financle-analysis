import sqlite3
import threading

from sonar.domain.holdings import HolderPosition, Row


class HoldingsRepo:
    """13F pozisyon deposu — `holdings` (son 2 çeyrek, prune edilir) + `symbol_quarterly`
    (kalıcı trend özeti). Amendment kuralı: RESTATEMENT o cik+quarter'ın eski satırlarını
    siler, NEW HOLDINGS / '' sadece ekler (spike B0)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        # ponytail: tek paylaşılan connection, global lock (bkz. store/cache.py).
        self._lock = threading.Lock()

    def ingest(self, rows: list[Row], quarter: str) -> None:
        restated_ciks = {r.cik for r in rows if r.amendment_type.upper() == "RESTATEMENT"}
        with self._lock:
            for cik in restated_ciks:
                self._conn.execute(
                    "DELETE FROM holdings WHERE quarter = ? AND cik = ?", (quarter, cik)
                )
            self._conn.executemany(
                """INSERT INTO holdings
                   (quarter, accession, cik, filer_name, cusip, issuer_name, shares, value, put_call)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        quarter,
                        r.accession,
                        r.cik,
                        r.filer_name,
                        r.cusip,
                        r.issuer_name,
                        r.shares,
                        r.value,
                        r.put_call,
                    )
                    for r in rows
                ],
            )
            self._conn.execute(
                """INSERT OR REPLACE INTO symbol_quarterly (cusip, quarter, total_shares, filer_count)
                   SELECT cusip, ?, SUM(shares), COUNT(DISTINCT cik)
                   FROM holdings WHERE quarter = ? AND put_call = ''
                   GROUP BY cusip""",
                (quarter, quarter),
            )
            self._conn.commit()

    def holders_of(self, cusip: str, quarter: str) -> list[HolderPosition]:
        with self._lock:
            cur = self._conn.execute(
                """SELECT cik, filer_name, shares, value, put_call FROM holdings
                   WHERE cusip = ? AND quarter = ? ORDER BY value DESC""",
                (cusip, quarter),
            )
            return [HolderPosition(*row) for row in cur.fetchall()]

    def filer_holdings(self, cik: str, quarter: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """SELECT cusip, issuer_name, shares, value, put_call FROM holdings
                   WHERE cik = ? AND quarter = ? ORDER BY value DESC""",
                (cik, quarter),
            )
            return [
                {"cusip": cusip, "issuer": issuer, "shares": shares, "value": value, "put_call": put_call}
                for cusip, issuer, shares, value, put_call in cur.fetchall()
            ]

    def quarters(self) -> list[str]:
        with self._lock:
            cur = self._conn.execute("SELECT DISTINCT quarter FROM holdings ORDER BY quarter")
            return [row[0] for row in cur.fetchall()]

    def trend(self, cusip: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """SELECT quarter, total_shares, filer_count FROM symbol_quarterly
                   WHERE cusip = ? ORDER BY quarter""",
                (cusip,),
            )
            return [
                {"quarter": quarter, "total_shares": total_shares, "filer_count": filer_count}
                for quarter, total_shares, filer_count in cur.fetchall()
            ]

    def prune(self, keep: int = 2) -> None:
        with self._lock:
            keep_quarters = [
                row[0]
                for row in self._conn.execute(
                    "SELECT DISTINCT quarter FROM holdings ORDER BY quarter DESC LIMIT ?", (keep,)
                ).fetchall()
            ]
            if not keep_quarters:
                return
            placeholders = ",".join("?" * len(keep_quarters))
            self._conn.execute(
                f"DELETE FROM holdings WHERE quarter NOT IN ({placeholders})", keep_quarters
            )
            self._conn.commit()
