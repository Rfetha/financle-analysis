from sonar.store.holdings_repo import HoldingsRepo
from sonar.domain.holdings import Row
from sonar.tools.holders import get_institutional_holders
from sonar.store.cache import Cache


def _seed(conn):
    repo = HoldingsRepo(conn)
    repo.ingest([Row("a", "1", "BERKSHIRE", "67066G104", "NVIDIA CORP", 500, 5000, "", "")], "2025Q4")
    repo.ingest(
        [
            Row("b", "1", "BERKSHIRE", "67066G104", "NVIDIA CORP", 0, 0, "", ""),
            Row("b", "2", "BOFA", "67066G104", "NVIDIA CORP", 1000, 10000, "", ""),
            Row("b", "2", "BOFA", "67066G104", "NVIDIA CORP", 200, 2000, "Put", ""),
        ],
        "2026Q1",
    )
    conn.execute("INSERT INTO cusip_ticker VALUES ('67066G104', 'NVDA')")
    conn.commit()
    return repo


def test_holders_returns_delta_and_options(conn):
    _seed(conn)
    out = get_institutional_holders("nvda", conn=conn, cache=Cache(conn), ttl=86400)
    assert out["quarter"] == "2026Q1"
    assert out["movers"][0]["filer_name"] == "BOFA"
    assert out["movers"][0]["action"] == "new"
    assert out["options"][0]["put_call"] == "Put"


def test_holders_carry_mandatory_provenance_note(conn):
    _seed(conn)
    out = get_institutional_holders("nvda", conn=conn, cache=Cache(conn), ttl=86400)
    note = out["provenance_note"]
    assert "13F" in note and "45 gün" in note
    assert "short" in note.lower() and "swap" in note.lower()  # verinin sınırı yazıyor


def test_unknown_ticker_returns_explicit_gap(conn):
    _seed(conn)
    out = get_institutional_holders("ZZZZ", conn=conn, cache=Cache(conn), ttl=86400)
    assert out["unavailable"]  # sessiz boş liste DEĞİL
