import httpx
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.us.edgar import EdgarClient

TICKERS = {
    "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
    "1": {"cik_str": 2488, "ticker": "AMD", "title": "ADVANCED MICRO DEVICES"},
    "2": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}
SUBMISSIONS = {
    "0001045810": {"sic": "3674", "sicDescription": "Semiconductors"},
    "0000002488": {"sic": "3674", "sicDescription": "Semiconductors"},
    "0000320193": {"sic": "3571", "sicDescription": "Electronic Computers"},
}


def _client() -> EdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "company_tickers.json" in url:
            return httpx.Response(200, json=TICKERS)
        for cik, payload in SUBMISSIONS.items():
            if cik in url:
                return httpx.Response(200, json=payload)
        return httpx.Response(404)

    http = HttpClient("Sonar/0.1 (t@e.com)", min_interval=0, transport=httpx.MockTransport(handler))
    return EdgarClient(http=http, now=lambda: 1.0)


def test_sic_lookup():
    assert _client().sic_for(Symbol("NVDA", "US")) == ("3674", "Semiconductors")


def test_peers_share_sic_and_exclude_self():
    peers = _client().peers(Symbol("NVDA", "US"))
    assert peers == ["AMD"]  # aynı SIC (3674), kendisi hariç, AAPL farklı SIC


import time
import pytest


@pytest.mark.slow
def test_real_peers_returns_same_sic_companies():
    # Why: naive SIC taraması gerçek EDGAR'da ~20s (her aday için submissions çağrısı; ABD'de
    # bulk ticker→SIC yok). Tool düzeyinde 24s cache tekrar maliyetini kaldırır; HIZLI yol
    # Faz B'de gelir (13F ingest ile tam SIC tablosu — plan §7 / A8 ponytail notu).
    # Bu test doğruluğu + "sonsuza kadar takılmıyor" sınırını korur, perf'i Faz B'ye bırakır.
    from sonar.market.us import _default_http

    client = EdgarClient(_default_http())
    started = time.perf_counter()
    peers = client.peers(Symbol("NVDA", "US"))
    elapsed = time.perf_counter() - started
    assert peers, "peers boş döndü"
    assert elapsed < 60.0, f"peers {elapsed:.1f}s — cold-scan makul sınırı aştı (hang?)"
