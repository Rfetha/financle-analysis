import httpx
import pytest
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol
from sonar.market.sources.http import HttpClient
from sonar.market.us.edgar import EdgarClient

TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
}

FACTS = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"form": "10-K", "fy": 2025, "fp": "FY", "val": 100.0, "end": "2025-12-31"},
                        {"form": "10-K", "fy": 2026, "fp": "FY", "val": 150.0, "end": "2026-12-31"},
                    ]
                }
            },
            "NetIncomeLoss": {
                "units": {
                    "USD": [
                        {"form": "10-K", "fy": 2026, "fp": "FY", "val": 30.0, "end": "2026-12-31"}
                    ]
                }
            },
        }
    }
}


def _client(routes: dict[str, dict]) -> EdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        for fragment, payload in routes.items():
            if fragment in str(request.url):
                return httpx.Response(200, json=payload)
        return httpx.Response(404)

    http = HttpClient("Sonar/0.1 (t@e.com)", min_interval=0, transport=httpx.MockTransport(handler))
    return EdgarClient(http=http, now=lambda: 1.0)


def test_cik_lookup_is_zero_padded():
    assert _client({"company_tickers.json": TICKERS}).cik_for("nvda") == "0001045810"


def test_unknown_ticker_raises():
    with pytest.raises(UnknownSymbol):
        _client({"company_tickers.json": TICKERS}).cik_for("ZZZZ")


def test_fundamentals_computes_margin_and_growth():
    client = _client({"company_tickers.json": TICKERS, "companyfacts": FACTS})
    f = client.fundamentals(Symbol("NVDA", "US"))
    assert f.revenue == 150.0
    assert f.net_income == 30.0
    assert f.net_margin == pytest.approx(20.0)        # 30/150
    assert f.revenue_growth_yoy == pytest.approx(50.0)  # 150 vs 100
    assert f.period == "FY2026"
    assert f.provenance.source == "SEC EDGAR companyfacts"


@pytest.mark.slow
def test_real_edgar_fundamentals():
    from sonar.market.us import _default_http

    client = EdgarClient(_default_http())
    f = client.fundamentals(Symbol("AAPL", "US"))
    assert f.revenue and f.revenue > 1e11  # Apple yıllık geliri 100B$ üstü
