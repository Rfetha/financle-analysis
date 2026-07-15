import pytest
from sonar.analytics.holdings import classify_delta, delta_report
from sonar.domain.holdings import HolderPosition


def _p(cik, name, shares, put_call=""):
    return HolderPosition(cik=cik, filer_name=name, shares=shares, value=shares * 10, put_call=put_call)


@pytest.mark.parametrize(
    "prev,cur,expected",
    [(0, 100, "new"), (100, 0, "exit"), (100, 150, "add"), (100, 60, "trim"), (100, 100, "hold")],
)
def test_classify_delta(prev, cur, expected):
    assert classify_delta(prev, cur) == expected


def test_delta_report_classifies_and_sorts_by_absolute_change():
    prev = [_p("1", "BOFA", 0), _p("2", "BERKSHIRE", 500), _p("3", "CITADEL", 100)]
    cur = [_p("1", "BOFA", 1000), _p("2", "BERKSHIRE", 0), _p("3", "CITADEL", 120)]
    out = delta_report(prev, cur, top=3)

    assert out["total_shares"] == 1120
    assert out["filer_count"] == 2                    # BERKSHIRE çıktı
    assert out["new"] == 1 and out["exit"] == 1
    assert out["movers"][0]["filer_name"] == "BOFA"   # en büyük mutlak değişim
    assert out["movers"][0]["action"] == "new"
    assert out["movers"][0]["delta_shares"] == 1000
    assert out["movers"][1]["action"] == "exit"


def test_delta_report_separates_option_positions():
    cur = [_p("1", "BOFA", 1000), _p("1", "BOFA", 200, "Put")]
    out = delta_report([], cur, top=5)
    assert out["total_shares"] == 1000               # opsiyon long hisseye KARIŞTIRILMAZ
    assert out["options"] == [{"filer_name": "BOFA", "put_call": "Put", "shares": 200}]
