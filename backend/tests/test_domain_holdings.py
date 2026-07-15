from sonar.domain.holdings import HolderPosition, Row, ShortInterest
from sonar.domain.insider import InsiderTrade
from sonar.domain.symbol import Symbol
from sonar.store.db import connect


def test_holdings_vos_construct():
    r = Row("a-1", "0001", "BOFA", "67066G104", "NVIDIA CORP", 1000, 10000, "", "RESTATEMENT")
    assert r.filer_name == "BOFA" and r.amendment_type == "RESTATEMENT"
    hp = HolderPosition("0001", "BOFA", 1000, 10000, "Put")
    assert hp.put_call == "Put"
    si = ShortInterest(Symbol("NVDA", "US"), 5_000_000, 2.5, "2026-06-30", "FINRA")
    assert si.days_to_cover == 2.5


def test_insider_trade_constructs():
    t = InsiderTrade("Jensen Huang", "CEO", "buy", 100, 120.5, 1783951200)
    assert t.action == "buy" and t.price == 120.5


def test_schema_creates_bigplayers_tables(tmp_path):
    conn = connect(tmp_path / "t.db")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"holdings", "symbol_quarterly", "cusip_ticker"} <= tables
    conn.close()
