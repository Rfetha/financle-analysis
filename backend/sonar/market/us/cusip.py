"""CUSIP ↔ ticker haritası. CUSIP lisanslı kimlik; ABD'de ücretsiz bulk ticker↔CUSIP yok.

Spike B0: 13F'in NAMEOFISSUER'ı her satırda dolu → issuer adını company_tickers.json ismiyle
eşleştirerek CUSIP→ticker kuruyoruz (likit isimlerde yüksek kapsam; obscure long-tail düşer).
Çıplak CUSIP hiç gösterilmez — ticker yoksa çağıran NAMEOFISSUER'a düşer.
"""

import re
import sqlite3

# Kurumsal ekleri ve noktalamayı at → "NVIDIA CORPORATION" ve "NVIDIA CORP" aynı anahtara iner.
_SUFFIX = re.compile(
    r"\b(THE|INC|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED|PLC|LP|LLC|HOLDINGS|HLDGS|GROUP|GRP|"
    r"CLASS|CL|COM|COMMON|STOCK|SA|NV|AG|ADR|ADS|NEW|DEL|DE|FUND|TRUST|ETF)\b"
)


def normalize_name(name: str) -> str:
    n = re.sub(r"[^A-Z0-9 ]", " ", name.upper())
    n = _SUFFIX.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip()


def build_pairs(cusip_names: dict[str, str], company_tickers: dict) -> list[tuple[str, str]]:
    """(cusip→issuer_name) + company_tickers.json → [(cusip, ticker)] isim eşleşenler.

    company_tickers: SEC company_tickers.json (values = {ticker, title, cik_str}).
    """
    name2ticker = {normalize_name(r["title"]): r["ticker"] for r in company_tickers.values()}
    out = []
    for cusip, issuer in cusip_names.items():
        ticker = name2ticker.get(normalize_name(issuer))
        if ticker:
            out.append((cusip, ticker))
    return out


class CusipMap:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def cusip_for(self, ticker: str) -> str | None:
        row = self._conn.execute(
            "SELECT cusip FROM cusip_ticker WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        return row[0] if row else None

    def ticker_for(self, cusip: str) -> str | None:
        row = self._conn.execute(
            "SELECT ticker FROM cusip_ticker WHERE cusip = ?", (cusip.upper(),)
        ).fetchone()
        return row[0] if row else None

    def load(self, pairs: list[tuple[str, str]]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO cusip_ticker (cusip, ticker) VALUES (?, ?)", pairs
        )
        self._conn.commit()
