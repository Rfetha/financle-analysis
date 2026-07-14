import httpx
import pytest
from sonar.market.sources.fred import FredClient
from sonar.market.sources.global_macro import GlobalMacro
from sonar.market.sources.http import HttpClient
from sonar.market.us.macro import USMacro

CSV = """DATE,VIXCLS,DTWEXBGS,DCOILWTICO
2026-07-10,14.2,121.5,78.4
2026-07-13,15.1,122.0,79.0
"""

US_CSV = """DATE,FEDFUNDS,CPIAUCSL,DGS10,DGS2
2025-07-13,5.0,300.0,4.1,4.5
2026-07-13,4.5,315.0,4.3,3.9
"""


def _fred(csv: str) -> FredClient:
    http = HttpClient(
        "Sonar/0.1 (t@e.com)", min_interval=0,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=csv)),
    )
    return FredClient(http)


def test_fred_latest_takes_last_non_empty_row():
    assert _fred(CSV).latest(["VIXCLS", "DTWEXBGS", "DCOILWTICO"]) == {
        "VIXCLS": 15.1, "DTWEXBGS": 122.0, "DCOILWTICO": 79.0
    }


def test_fred_skips_missing_values():
    csv = "DATE,VIXCLS\n2026-07-12,14.0\n2026-07-13,.\n"
    assert _fred(csv).latest(["VIXCLS"]) == {"VIXCLS": 14.0}  # FRED boş değeri "." yazar


def test_global_snapshot():
    g = GlobalMacro(_fred(CSV)).snapshot()
    assert g.vix == 15.1 and g.dxy == 122.0 and g.wti == 79.0


def test_us_snapshot_computes_curve_and_cpi_yoy():
    local = USMacro(_fred(US_CSV)).snapshot()
    assert local.fed_funds == 4.5
    assert local.yield_10y == 4.3 and local.yield_2y == 3.9
    assert local.curve_10y_2y == pytest.approx(0.4)   # 4.3 - 3.9
    assert local.cpi_yoy == pytest.approx(5.0)        # 315 vs 300, yıllık


@pytest.mark.slow
def test_real_fred_returns_vix():
    from sonar.market.us import _default_http

    snap = GlobalMacro(FredClient(_default_http())).snapshot()
    assert snap.vix and 5 < snap.vix < 100  # VIX makul aralıkta
