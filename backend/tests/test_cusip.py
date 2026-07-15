from sonar.market.us.cusip import CusipMap, build_pairs, normalize_name
from sonar.store.db import connect


def test_normalize_collapses_corporate_suffixes():
    assert normalize_name("NVIDIA CORPORATION") == normalize_name("NVIDIA CORP") == "NVIDIA"


def test_build_pairs_matches_by_name():
    cusip_names = {"67066G104": "NVIDIA CORPORATION", "999999999": "OBSCURE HOLDINGS XYZ"}
    tickers = {"0": {"cik_str": 1, "ticker": "NVDA", "title": "NVIDIA CORP"}}
    pairs = build_pairs(cusip_names, tickers)
    assert pairs == [("67066G104", "NVDA")]  # obscure eşleşmez → düşer


def test_cusip_map_roundtrip(tmp_path):
    conn = connect(tmp_path / "t.db")
    m = CusipMap(conn)
    m.load([("67066G104", "NVDA")])
    assert m.cusip_for("nvda") == "67066G104"
    assert m.ticker_for("67066G104") == "NVDA"
    assert m.cusip_for("ZZZZ") is None
    conn.close()
