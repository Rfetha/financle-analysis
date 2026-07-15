import httpx
import pytest
from sonar.market.sources.fred import FredClient
from sonar.market.sources.global_macro import GlobalMacro
from sonar.market.sources.http import HttpClient
from sonar.market.us.macro import USMacro

# Gerçek FRED: tek id → düz CSV, tarih kolonu "observation_date", değer kolonu id'nin kendisi.
CSVS = {
    "VIXCLS": "observation_date,VIXCLS\n2026-07-10,14.2\n2026-07-13,15.1\n",
    "DTWEXBGS": "observation_date,DTWEXBGS\n2026-07-10,121.5\n2026-07-13,122.0\n",
    "DCOILWTICO": "observation_date,DCOILWTICO\n2026-07-10,78.4\n2026-07-13,79.0\n",
    "FEDFUNDS": "observation_date,FEDFUNDS\n2026-07-13,4.5\n",
    "DGS10": "observation_date,DGS10\n2026-07-13,4.3\n",
    "DGS2": "observation_date,DGS2\n2026-07-13,3.9\n",
    "CPIAUCSL": "observation_date,CPIAUCSL\n2025-07-13,300.0\n2026-07-13,315.0\n",
}


def _fred(responses: dict[str, str] | None = None) -> FredClient:
    """MockTransport, istek URL'sindeki `id=` parametresine göre ilgili tek-seri CSV'sini döner."""
    csvs = responses if responses is not None else CSVS

    def handler(request: httpx.Request) -> httpx.Response:
        sid = request.url.params.get("id")
        return httpx.Response(200, text=csvs[sid])

    http = HttpClient(
        "Sonar/0.1 (t@e.com)", min_interval=0,
        transport=httpx.MockTransport(handler),
    )
    return FredClient(http)


def test_fred_latest_takes_last_non_empty_row():
    assert _fred().latest(["VIXCLS", "DTWEXBGS", "DCOILWTICO"]) == {
        "VIXCLS": 15.1, "DTWEXBGS": 122.0, "DCOILWTICO": 79.0
    }


def test_fred_skips_missing_values():
    csv = {"VIXCLS": "observation_date,VIXCLS\n2026-07-12,14.0\n2026-07-13,.\n"}
    assert _fred(csv).latest(["VIXCLS"]) == {"VIXCLS": 14.0}  # FRED boş değeri "." yazar


def test_global_snapshot():
    g = GlobalMacro(_fred()).snapshot()
    assert g.vix == 15.1 and g.dxy == 122.0 and g.wti == 79.0


def test_us_snapshot_computes_curve_and_cpi_yoy():
    local = USMacro(_fred()).snapshot()
    assert local.fed_funds == 4.5
    assert local.yield_10y == 4.3 and local.yield_2y == 3.9
    assert local.curve_10y_2y == pytest.approx(0.4)   # 4.3 - 3.9
    assert local.cpi_yoy == pytest.approx(5.0)        # 315 vs 300, yıllık


@pytest.mark.slow
def test_real_fred_returns_vix():
    from sonar.market.us import _default_http

    snap = GlobalMacro(FredClient(_default_http())).snapshot()
    assert snap.vix and 5 < snap.vix < 100  # VIX makul aralıkta
