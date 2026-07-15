import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  expires_at REAL NOT NULL
);

-- 13F pozisyonları (Big Players). Ham veri son 2 çeyrek; trend için özet tablosu kalıcı (spec §7).
CREATE TABLE IF NOT EXISTS holdings (
  quarter     TEXT NOT NULL,
  accession   TEXT NOT NULL,
  cik         TEXT NOT NULL,
  filer_name  TEXT NOT NULL,
  cusip       TEXT NOT NULL,
  issuer_name TEXT NOT NULL,
  shares      INTEGER NOT NULL,
  value       INTEGER NOT NULL,
  put_call    TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_holdings_cusip ON holdings(cusip, quarter);
CREATE INDEX IF NOT EXISTS idx_holdings_cik   ON holdings(cik, quarter);

-- Sahiplik trendi — ham veri silinse de yaşar (sembol başına çeyrekte 1 satır).
CREATE TABLE IF NOT EXISTS symbol_quarterly (
  cusip        TEXT NOT NULL,
  quarter      TEXT NOT NULL,
  total_shares INTEGER NOT NULL,
  filer_count  INTEGER NOT NULL,
  PRIMARY KEY (cusip, quarter)
);

-- CUSIP <-> ticker haritası (isim eşleşmesiyle kurulur; çıplak CUSIP hiç gösterilmez).
CREATE TABLE IF NOT EXISTS cusip_ticker (
  cusip  TEXT PRIMARY KEY,
  ticker TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cusip_ticker_ticker ON cusip_ticker(ticker);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn
