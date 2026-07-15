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
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"

# Why: XBRL'de aynı kavram farklı etiketlerle raporlanır (şirket/yıl bazında değişir).
# Sırayla dene, ilk bulunanı al.
REVENUE_TAGS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet")
INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")


def _filed_key(entry: dict) -> str:
    """Sıralama anahtarı: hangi filing daha yeni? `filed` (ISO tarih) tercih edilir,
    yoksa `accn` (accession number, artan sırada) fallback."""
    return entry.get("filed") or entry.get("accn") or ""


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
                    return sorted(self._dedup_by_end(annual), key=lambda u: u["end"])
        return []

    @staticmethod
    def _dedup_by_end(entries: list[dict]) -> list[dict]:
        """Aynı fiscal year birden fazla 10-K'da yeniden raporlanır (bu yılki 10-K +
        gelecek yılki 10-K'nın prior-year karşılaştırması). `end` başına, en son
        FILE EDİLEN (`filed`, yoksa `accn`) kazanır."""
        by_end: dict[str, dict] = {}
        for entry in entries:
            key = entry["end"]
            existing = by_end.get(key)
            if existing is None or _filed_key(entry) > _filed_key(existing):
                by_end[key] = entry
        return list(by_end.values())

    def fundamentals(self, symbol: Symbol) -> Fundamentals:
        facts = self.company_facts(self.cik_for(symbol.ticker))
        revenues = self._annual(facts, REVENUE_TAGS)
        incomes = self._annual(facts, INCOME_TAGS)
        if not revenues:
            raise UnknownSymbol(f"{symbol.ticker}: XBRL geliri yok")

        latest = revenues[-1]
        prior = revenues[-2] if len(revenues) > 1 else None
        revenue = float(latest["val"])
        matching_income = next((i for i in incomes if i["end"] == latest["end"]), None)
        net_income = float(matching_income["val"]) if matching_income is not None else None
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

    def submissions(self, cik: str) -> dict:
        return self._http.get_json(SUBMISSIONS_URL.format(cik=cik))

    def sic_for(self, symbol: Symbol) -> tuple[str, str]:
        data = self.submissions(self.cik_for(symbol.ticker))
        return data.get("sic", ""), data.get("sicDescription", "")

    def peers(self, symbol: Symbol, limit: int = 8) -> list[str]:
        """Aynı SIC kodundaki diğer şirketler.

        ponytail: her ticker için submissions çağrısı gerekiyor → CIK haritasının tamamını
        taramak 10.000+ istek olurdu. Bu yüzden yalnız CIK'i hedefe YAKIN olanlara bakılır:
        SEC CIK'leri kayıt sırasına göre verir, aynı sektör şirketleri kümelenmez — o yüzden
        tarama sırası rastgele değil, *tam liste üzerinde sınırlı* tutulur (limit'e ulaşınca dur).
        Daha iyi kapsam gerekirse Faz B'de 13F ingest'iyle birlikte gelen tam SIC tablosu kullanılır.
        """
        if self._cik_map is None:
            self.cik_for(symbol.ticker)
        assert self._cik_map is not None
        target_sic, _ = self.sic_for(symbol)
        if not target_sic:
            return []
        out: list[str] = []
        for ticker in self._cik_map:
            if ticker == symbol.ticker or len(out) >= limit:
                continue
            try:
                sic, _ = self.sic_for(Symbol(ticker, symbol.market))
            except Exception:  # noqa: BLE001 — tek bir sembolün 404'ü peers'ı düşürmesin
                continue
            if sic == target_sic:
                out.append(ticker)
        return out

    def insider_trades(self, symbol: Symbol, limit: int = 30) -> list["InsiderTrade"]:
        """Issuer'ın son Form 4'leri. 2 iş günü gecikmeli, gerçek isim (spec §2)."""
        from defusedxml import ElementTree

        from sonar.domain.insider import InsiderTrade

        cik = self.cik_for(symbol.ticker)
        subs = self.submissions(cik)
        recent = subs.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])

        out: list[InsiderTrade] = []
        for form, acc, doc in zip(forms, accessions, docs):
            if form != "4" or len(out) >= limit:
                continue
            xml = self._http.get_text(
                ARCHIVE_URL.format(cik=int(cik), acc_nodash=acc.replace("-", ""), doc=doc)
            )
            out.extend(_parse_form4(ElementTree.fromstring(xml)))
        return out


def _parse_form4(root) -> list["InsiderTrade"]:
    from datetime import datetime

    from sonar.domain.insider import InsiderTrade

    name = root.findtext(".//reportingOwnerId/rptOwnerName") or "?"
    title = root.findtext(".//reportingOwnerRelationship/officerTitle") or ""
    trades = []
    for tx in root.iter("nonDerivativeTransaction"):
        code = tx.findtext(".//transactionCode") or ""
        if code != "P" and code != "S":  # P = açık piyasa alımı, S = satış (gerisi hibe/vergi vs.)
            continue
        date_text = tx.findtext(".//transactionDate/value") or ""
        shares = tx.findtext(".//transactionShares/value") or "0"
        price = tx.findtext(".//transactionPricePerShare/value")
        trades.append(
            InsiderTrade(
                name=name,
                title=title,
                action="buy" if code == "P" else "sell",
                shares=int(float(shares)),
                price=float(price) if price else None,
                traded_at=int(datetime.fromisoformat(date_text).timestamp()) if date_text else 0,
            )
        )
    return trades
