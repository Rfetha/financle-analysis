"""SEC EDGAR — resmî, ücretsiz, key'siz. Rate-limit ve User-Agent zorunlu (HttpClient uygular).

Bu istemci üç yeteneğin tabanı: fundamentals (companyfacts), peers (SIC), ve Faz B'de 13F/Form 4.
"""

import time
from typing import Callable

from sonar.domain.fundamentals import Fundamentals
from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol
from sonar.market.sources.http import HttpClient

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# Why: XBRL'de aynı kavram farklı etiketlerle raporlanır (şirket/yıl bazında değişir).
# Sırayla dene, ilk bulunanı al.
REVENUE_TAGS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet")
INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")


class EdgarClient:
    source = "SEC EDGAR companyfacts"

    def __init__(self, http: HttpClient, now: Callable[[], float] = time.time) -> None:
        self._http = http
        self._now = now
        self._cik_map: dict[str, str] | None = None

    def cik_for(self, ticker: str) -> str:
        if self._cik_map is None:
            raw = self._http.get_json(TICKERS_URL)
            self._cik_map = {
                row["ticker"].upper(): f"{int(row['cik_str']):010d}" for row in raw.values()
            }
        cik = self._cik_map.get(ticker.upper())
        if cik is None:
            raise UnknownSymbol(ticker)
        return cik

    def company_facts(self, cik: str) -> dict:
        return self._http.get_json(FACTS_URL.format(cik=cik))

    def _annual(self, facts: dict, tags: tuple[str, ...]) -> list[dict]:
        gaap = facts.get("facts", {}).get("us-gaap", {})
        for tag in tags:
            units = gaap.get(tag, {}).get("units", {}).get("USD")
            if units:
                annual = [u for u in units if u.get("fp") == "FY" and u.get("form") == "10-K"]
                if annual:
                    return sorted(annual, key=lambda u: u["end"])
        return []

    def fundamentals(self, symbol: Symbol) -> Fundamentals:
        facts = self.company_facts(self.cik_for(symbol.ticker))
        revenues = self._annual(facts, REVENUE_TAGS)
        incomes = self._annual(facts, INCOME_TAGS)
        if not revenues:
            raise UnknownSymbol(f"{symbol.ticker}: XBRL geliri yok")

        latest = revenues[-1]
        prior = revenues[-2] if len(revenues) > 1 else None
        revenue = float(latest["val"])
        net_income = float(incomes[-1]["val"]) if incomes else None
        growth = (
            round((revenue - float(prior["val"])) / float(prior["val"]) * 100, 2)
            if prior and float(prior["val"])
            else None
        )
        margin = round(net_income / revenue * 100, 2) if net_income is not None and revenue else None
        return Fundamentals(
            symbol=symbol,
            period=f"FY{latest['fy']}",
            revenue=revenue,
            net_income=net_income,
            net_margin=margin,
            revenue_growth_yoy=growth,
            provenance=Provenance(self.source, self._now()),
        )
