import time
from datetime import datetime

import httpx
from defusedxml import ElementTree

from sonar.analytics.insiders import cluster
from sonar.domain.insider import InsiderTrade
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.market.sources.http import HttpClient
from sonar.market.us.edgar import EdgarClient, _parse_form4
from sonar.store.cache import Cache
from sonar.tools.insiders import get_insider_trades

DAY = 86400


def _t(name, action, shares, day):
    return InsiderTrade(
        name=name, title="CFO", action=action, shares=shares, price=10.0, traded_at=day * DAY
    )


def test_cluster_buy_needs_multiple_distinct_insiders():
    trades = [_t("A", "buy", 100, 30), _t("B", "buy", 200, 25), _t("C", "buy", 50, 10)]
    out = cluster(trades, window_days=30, now=31 * DAY)
    assert out["buyers"] == 3
    assert out["sellers"] == 0
    assert out["is_cluster_buy"] is True


def test_single_buyer_is_not_a_cluster():
    out = cluster([_t("A", "buy", 100, 30)], window_days=30, now=31 * DAY)
    assert out["is_cluster_buy"] is False  # tek CEO alımı gürültü (spec §7)


def test_trades_outside_window_are_ignored():
    trades = [_t("A", "buy", 100, 1), _t("B", "buy", 100, 2), _t("C", "buy", 100, 3)]
    out = cluster(trades, window_days=30, now=100 * DAY)
    assert out["buyers"] == 0 and out["is_cluster_buy"] is False


def test_selling_counted_separately():
    out = cluster([_t("A", "sell", 100, 30), _t("B", "sell", 50, 29)], window_days=30, now=31 * DAY)
    assert out["sellers"] == 2 and out["is_cluster_buy"] is False


FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <schemaVersion>X0508</schemaVersion>
  <documentType>4</documentType>
  <issuer>
    <issuerCik>0001045810</issuerCik>
    <issuerName>NVIDIA CORP</issuerName>
    <issuerTradingSymbol>NVDA</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>HUANG JEN-HSUN</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>President and CEO</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2024-01-15</value></transactionDate>
      <transactionCoding>
        <transactionFormType>4</transactionFormType>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionPricePerShare><value>495.23</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2024-01-16</value></transactionDate>
      <transactionCoding>
        <transactionFormType>4</transactionFormType>
        <transactionCode>S</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>500</value></transactionShares>
        <transactionPricePerShare><value>500.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2024-01-17</value></transactionDate>
      <transactionCoding>
        <transactionFormType>4</transactionFormType>
        <transactionCode>A</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>2000</value></transactionShares>
        <transactionPricePerShare><value>0</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def test_parse_form4_skips_non_signal_codes():
    trades = _parse_form4(ElementTree.fromstring(FORM4_XML))

    assert len(trades) == 2  # A (hibe) atlanir
    assert trades[0] == InsiderTrade(
        name="HUANG JEN-HSUN", title="President and CEO", action="buy",
        shares=1000, price=495.23,
        traded_at=int(datetime.fromisoformat("2024-01-15").timestamp()),
    )
    assert trades[1].action == "sell"
    assert trades[1].shares == 500


SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["4", "10-K", "4"],
            "accessionNumber": ["0001234567-24-000001", "0001234567-24-000002", "0001234567-24-000003"],
            "primaryDocument": ["form4-1.xml", "10k.htm", "form4-2.xml"],
        }
    }
}


def _edgar_client() -> EdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "company_tickers.json" in url:
            return httpx.Response(200, json={"0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}})
        if "submissions" in url:
            return httpx.Response(200, json=SUBMISSIONS)
        if "form4" in url:
            return httpx.Response(200, text=FORM4_XML)
        return httpx.Response(404)

    http = HttpClient("Sonar/0.1 (t@e.com)", min_interval=0, transport=httpx.MockTransport(handler))
    return EdgarClient(http=http, now=lambda: 1.0)


def test_insider_trades_only_fetches_form4_filings():
    trades = _edgar_client().insider_trades(Symbol("NVDA", "US"))
    assert len(trades) == 4  # 2 Form 4 dosyasi x (P + S)
    assert {t.action for t in trades} == {"buy", "sell"}


def test_insider_trades_respects_limit():
    trades = _edgar_client().insider_trades(Symbol("NVDA", "US"), limit=1)
    assert len(trades) == 2  # ilk Form 4'ten gelen P+S, limit ikinci dosyayi durdurur


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_insider_trades(self, symbol):
        recent = time.time() - DAY
        return [
            InsiderTrade(name="A", title="CFO", action="buy", shares=100, price=10.0, traded_at=int(recent)),
            InsiderTrade(name="B", title="COO", action="buy", shares=200, price=10.0, traded_at=int(recent)),
        ]


def test_get_insider_trades_tool_shape(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    out = get_insider_trades("nvda", registry=reg, cache=Cache(conn), ttl=86400)

    assert out["ticker"] == "NVDA"
    assert len(out["trades"]) == 2
    assert out["cluster"]["buyers"] == 2
    assert out["provenance_note"] == (
        "Form 4 · 2 iş günü gecikmeli · yalnız açık piyasa alım/satımı (hibe/vergi hariç)."
    )


import pytest
from sonar.market.us import _default_http


@pytest.mark.slow
def test_real_form4_parses():
    trades = EdgarClient(_default_http()).insider_trades(Symbol("NVDA", "US"), limit=3)
    assert all(t.action in ("buy", "sell") for t in trades)
