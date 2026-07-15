"""13F ingestion — uygulama açılışında arka planda. Durum GÖRÜNÜR (spec §7: sessiz indirme yok).

spike B0 düzeltmesi: dosya adları tarih-aralıklı (ör. "01mar2026-31may2026_form13f.zip"),
şablonla üretilemez — index sayfasından (`thirteen_f.DERA_INDEX_URL`) keşfedilir.
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Callable

from loguru import logger

from sonar.market.sources.http import HttpClient
from sonar.market.us.cusip import CusipMap, build_pairs
from sonar.market.us.thirteen_f import DERA_INDEX_URL, parse_13f_zip
from sonar.store.holdings_repo import HoldingsRepo

# Örnek href: "/files/structureddata/data/form-13f-data-sets/01mar2026-31may2026_form13f.zip"
_ZIP_HREF = re.compile(
    r'href="([^"]*/(\d{2}[a-zA-Z]{3}\d{4}-\d{2}[a-zA-Z]{3}\d{4})_form13f\.zip)"'
)


@dataclass
class IngestState:
    status: str = "idle"  # idle | running | ready | error
    progress: float = 0.0
    quarter: str = ""
    message: str = ""


def _latest_periods(index_html: str, n: int = 2) -> list[tuple[str, str]]:
    """Index HTML'den en yeni n dönemi çıkar: [(quarter_label, zip_url), ...], sayfadaki sırayla
    (en yeni önce — spike B0: index sayfası .zip'leri en yeniden eskiye listeler)."""
    out: list[tuple[str, str]] = []
    for href, date_range in _ZIP_HREF.findall(index_html):
        url = href if href.startswith("http") else f"https://www.sec.gov{href}"
        out.append((date_range.lower(), url))
        if len(out) >= n:
            break
    return out


class Ingester:
    def __init__(
        self,
        repo: HoldingsRepo,
        cusip_map: CusipMap,
        http: HttpClient,
        tickers: dict,
        fetch_index: Callable[[], str] | None = None,
    ) -> None:
        self._repo = repo
        self._cusip_map = cusip_map
        self._http = http
        self._tickers = tickers
        self._fetch_index = fetch_index or (lambda: http.get_text(DERA_INDEX_URL))
        self.state = IngestState()

    def _ingest_period(self, quarter: str, url: str) -> int:
        """Blocking: indir + parse + cusip↔ticker eşle + obscure long-tail'i filtrele + yaz."""
        data = self._http.get_bytes(url)
        rows = list(parse_13f_zip(data))
        cusip_names = {r.cusip: r.issuer_name for r in rows}
        pairs = build_pairs(cusip_names, self._tickers)
        self._cusip_map.load(pairs)
        # Why: çıplak CUSIP hiç gösterilmez (spike B0) — ticker'a çözülemeyen satırlar düşer.
        filtered = [r for r in rows if self._cusip_map.ticker_for(r.cusip) is not None]
        self._repo.ingest(filtered, quarter)
        return len(filtered)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        self.state = IngestState(status="running")
        try:
            index_html = await loop.run_in_executor(None, self._fetch_index)
            periods = _latest_periods(index_html)
            if not periods:
                raise RuntimeError("13F index sayfasında .zip bulunamadı")
            existing = set(self._repo.quarters())
            for i, (quarter, url) in enumerate(periods):
                self.state.quarter = quarter
                if quarter in existing:
                    logger.info("13F {} zaten var — atlanıyor", quarter)
                else:
                    logger.info("13F {} indiriliyor… ({})", quarter, url)
                    n = await loop.run_in_executor(None, self._ingest_period, quarter, url)
                    logger.info("13F {} yüklendi: {} satır (cusip eşleşen)", quarter, n)
                self.state.progress = (i + 1) / len(periods)
            await loop.run_in_executor(None, self._repo.prune, 2)
            self.state.status = "ready"
        except asyncio.CancelledError:
            raise  # Why: uygulama kapanışı/iptal — yutma, propagate et (CLAUDE.md §5)
        except Exception as e:  # noqa: BLE001
            # Why: ingestion çökerse uygulama ayakta kalmalı (Faz A çalışıyor), ama hata GÖRÜNMELİ.
            logger.exception("13F ingestion çöktü")
            self.state.status = "error"
            self.state.message = f"{type(e).__name__}: {e}"
