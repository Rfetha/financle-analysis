# M2 — Deep Analysis + Big Players Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Tek hisse için top-down derin analiz (makro→mikro→teknik→haber) + büyük oyuncular (13F/Form 4)
üretmek; çıktı: akan rapor + interaktif grafik + canlı fiyat.

**Architecture:** Deep tool'lar hesaplanmış sonuç döner (LLM aritmetik yapmaz). Matematik `analytics/`
çekirdeğinde, "hangi URL/format" `market/us/` plugin'inde, "nasıl HTTP çekilir" `market/sources/` ortak
makinesinde. DeepAnalysis = deterministik LangGraph StateGraph: `gather` (LLM yok, paralel tool) →
`synthesize` (tek LLM çağrısı, token-token akar). Fiyat kaynağı Strategy (Alpaca | yfinance).

**Tech Stack:** Python 3.12 · FastAPI · LangGraph · httpx · pandas/numpy (göstergeler **elle**) ·
raw sqlite3 · Vite+React+TS · Lightweight Charts · uv · pytest

**Spec:** `docs/superpowers/specs/2026-07-13-m2-deep-analysis-and-big-players-design.md`

## Global Constraints

- **Katman sınırı testli:** `api/ tools/ domain/ store/ market/ analytics/` içinde `langchain*`,
  `langgraph`, `openai`, `anthropic` **ithal edilemez** (`tests/test_layering.py`).
- **Deep tool (ADR-0003):** tool hesaplanmış/yapılandırılmış dict döner. LLM aritmetik yapmaz.
- **Sabit tool yüzeyi (ADR-0001/0005):** market veremediği yeteneğe `Unsupported` fırlatır — sessiz boş yok.
- **Teknik göstergeler elle yazılır** (numpy/pandas). TA-Lib / pandas-ta **yasak** (ADR-0006).
- **Tek SQLite** (ADR-0004): DB + TTL cache + history. Redis/vector DB yok.
- **Uniform SSE (ADR-0008):** event taksonomisi genişler, yeniden yazılmaz.
- **EDGAR nezaketi:** her SEC isteğinde `User-Agent: Sonar/0.1 (<contact>)` + ≤10 req/s. İhlal = IP ban.
- **Provenance zorunlu:** dışarıdan gelen her veri kaynak + zaman taşır; 13F çıktısı gecikme notunu taşır.
- **Yapısal ve davranışsal değişiklik ayrı commit** (CLAUDE.md §3).
- **Testler:** deterministik unit varsayılan; gerçek ağ çağrısı `@pytest.mark.slow`.
- Komutlar `backend/` içinden: `uv run pytest` · `uv run pytest -m slow` · `uv run sonar`.

## Yeni bağımlılıklar (gerekçeli)

| Paket | Neden | Nereye |
|---|---|---|
| `pandas>=2.2`, `numpy>=1.26` | gösterge matematiği (zaten yfinance ile geliyor — açıkça beyan) | backend |
| `websockets>=13` | Alpaca canlı fiyat stream'i (Task A14) | backend |
| `lightweight-charts` | interaktif mum grafiği | frontend |

Yeni provider/LLM bağımlılığı **yok**.

## Dosya haritası

```
backend/sonar/
  analytics/__init__.py
  analytics/indicators.py      RSI · EMA · MACD · BB · S/R · OBV · hacim anomalisi   (saf, I/O yok)
  analytics/holdings.py        (B) 13F Δ sınıflaması · float % · özet satır
  analytics/insiders.py        (B) Form 4 cluster
  domain/candle.py             Candle · OhlcvSeries
  domain/fundamentals.py       Fundamentals
  domain/news.py               NewsItem
  domain/macro.py              MacroSnapshot · GlobalSnapshot · LocalSnapshot
  domain/holdings.py           (B) HolderPosition · HoldingsSnapshot · InsiderTrade · ShortInterest
  market/base.py               MarketPlugin (Protocol) + BaseMarketPlugin (ABC: Unsupported varsayılan)
  market/sources/http.py       rate-limitli httpx (User-Agent, retry, backoff)
  market/sources/fred.py       FredClient — key'siz CSV
  market/sources/global_macro.py  GlobalMacro (VIX · DXY · WTI) — FRED üstünden
  market/sources/rss.py        RSS → NewsItem
  market/us/__init__.py        USMarketPlugin (composer)
  market/us/prices.py          PriceSource Protocol → AlpacaPrices | YFinancePrices   (Strategy)
  market/us/edgar.py           ticker↔CIK · companyfacts · SIC · (B) 13F · Form 4
  market/us/macro.py           USMacro (FEDFUNDS · CPI · DGS10 · DGS2 · eğri)
  market/us/news.py            US feed listesi
  market/us/finra.py           (B) short interest
  tools/_cache.py              cached(cache, key, ttl, fn) — 11 tool'un cache sarmalı tek yerde
  tools/{ohlcv,technicals,fundamentals,news,macro,peers}.py
  tools/{holders,insiders,short_interest}.py   (B)
  store/holdings_repo.py       (B) 13F SQLite şeması + ingest + sorgu
  agent/recipes/deep_analysis.py   StateGraph
  agent/events.py              + analysis-step · chart · quote-tick
  api/app.py                   + POST /api/analyze · GET /api/ohlcv · GET /api/stream/quotes · (B) /api/ingest/status
frontend/src/
  chart.tsx · analysis.tsx · parts.tsx (registry) · quotes.ts
```

---

# FAZ A — Derin analiz *(shippable; sonunda merge kapısı)*

### Task A1: `market/us.py` → `market/us/` paketi + sözleşme genişler

Yapısal değişiklik — **davranış aynı kalır**. Mevcut 14 test yeşil kalmalı.

**Files:**
- Create: `backend/sonar/market/us/__init__.py`, `backend/sonar/market/us/prices.py`
- Delete: `backend/sonar/market/us.py`
- Modify: `backend/sonar/market/base.py`
- Test: `backend/tests/test_us_plugin.py` (mevcut, değişmeden geçmeli), `backend/tests/test_market_base.py` (yeni)

**Interfaces:**
- Produces: `MarketPlugin` Protocol (11 metot) · `BaseMarketPlugin` ABC (Unsupported varsayılanları) ·
  `PriceSource` Protocol (`quote(symbol) -> Quote`) · `YFinancePrices` · `USMarketPlugin(prices: PriceSource)`

- [ ] **Step 1: Failing test — Unsupported varsayılanı**

`backend/tests/test_market_base.py`:
```python
import pytest
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin, Unsupported


class BareMarket(BaseMarketPlugin):
    market = "BARE"


def test_unimplemented_capability_raises_unsupported():
    plugin = BareMarket()
    with pytest.raises(Unsupported, match="BARE: ohlcv"):
        plugin.get_ohlcv(Symbol("AAPL", "BARE"), "6mo", "1d")


def test_unimplemented_holders_raises_unsupported():
    with pytest.raises(Unsupported, match="BARE: 13F"):
        BareMarket().get_institutional_holders(Symbol("AAPL", "BARE"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_market_base.py -v`
Expected: FAIL — `ImportError: cannot import name 'BaseMarketPlugin'`

- [ ] **Step 3: `market/base.py` — Protocol + ABC**

```python
"""Market sözleşmesi (ADR-0001/0005).

MarketPlugin = Protocol: yapısal sözleşme. Üçüncü-parti paket (sonar-market-tr) bize
bağlanmadan implement edebilsin diye nominal hiyerarşi dayatmıyoruz.

BaseMarketPlugin = opsiyonel ABC: tek işi *sözleşme bozunumu* — verilmeyen her yetenek
Unsupported fırlatır. Market yalnız verebildiğini override eder. (Protocol'de eksik metot
AttributeError'a düşer; bu ADR-0005'in açık cevabı değil.)
"""

from typing import Protocol, runtime_checkable

from sonar.domain.candle import OhlcvSeries
from sonar.domain.fundamentals import Fundamentals
from sonar.domain.macro import MacroSnapshot
from sonar.domain.news import NewsItem
from sonar.domain.quote import Quote
from sonar.domain.symbol import Symbol


class Unsupported(Exception):
    """Market bu yeteneği sağlayamıyor."""


class UnknownSymbol(Exception):
    """Market'te böyle bir sembol yok / veri bulunamadı."""


@runtime_checkable
class MarketPlugin(Protocol):
    market: str

    def get_quote(self, symbol: Symbol) -> Quote: ...
    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries: ...
    def get_fundamentals(self, symbol: Symbol) -> Fundamentals: ...
    def get_news(self, symbol: Symbol) -> list[NewsItem]: ...
    def get_peers(self, symbol: Symbol) -> list[str]: ...
    def get_macro_snapshot(self) -> MacroSnapshot: ...


class BaseMarketPlugin:
    """11 yeteneğin Unsupported varsayılanı."""

    market: str = "?"

    def get_quote(self, symbol: Symbol) -> Quote:
        raise Unsupported(f"{self.market}: quote")

    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        raise Unsupported(f"{self.market}: ohlcv")

    def get_fundamentals(self, symbol: Symbol) -> Fundamentals:
        raise Unsupported(f"{self.market}: fundamentals")

    def get_news(self, symbol: Symbol) -> list[NewsItem]:
        raise Unsupported(f"{self.market}: news")

    def get_peers(self, symbol: Symbol) -> list[str]:
        raise Unsupported(f"{self.market}: peers")

    def get_macro_snapshot(self) -> MacroSnapshot:
        raise Unsupported(f"{self.market}: macro")

    def get_institutional_holders(self, symbol: Symbol):
        raise Unsupported(f"{self.market}: 13F")

    def get_insider_trades(self, symbol: Symbol):
        raise Unsupported(f"{self.market}: Form 4")

    def get_filer_holdings(self, filer_cik: str):
        raise Unsupported(f"{self.market}: 13F filer")

    def get_short_interest(self, symbol: Symbol):
        raise Unsupported(f"{self.market}: short interest")
```

> **Not:** `BaseMarketPlugin` bir `ABC` değil düz sınıf — `abstractmethod` yok, çünkü hiçbir metot
> zorunlu değil (market ne verebiliyorsa onu verir). `ABC` ilan etmek boş bir tören olurdu.

Bu adımda `domain/candle.py`, `domain/fundamentals.py`, `domain/news.py`, `domain/macro.py` henüz yok →
Task A4/A7/A9/A10'da geliyor. Şimdilik import'ları **geçici olarak** yazma; yalnız `Quote`/`Symbol`
import et ve tip anotasyonlarını string yap:

```python
    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> "OhlcvSeries":
```
…ve dosyanın başına `from __future__ import annotations` koy. İlgili VO'lar geldikçe import'lar
gerçek hale gelir (Task A4'te `TYPE_CHECKING` bloğuna alınır).

- [ ] **Step 4: `market/us/prices.py` — PriceSource Strategy (yfinance)**

```python
"""Fiyat kaynağı = Strategy (GoF). Aynı interface, key'in varlığına göre değişen davranış.
Alpaca (resmî, sözleşmeli) Task A3'te eklenir; bu dosyada bugünkü yfinance yolu korunur.
"""

import time
from decimal import Decimal
from typing import Callable, Protocol

from sonar.domain.money import Money
from sonar.domain.quote import Provenance, Quote
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol


class PriceSource(Protocol):
    name: str

    def quote(self, symbol: Symbol) -> Quote: ...


def _yfinance_fetch(ticker: str) -> tuple[float, float]:
    import yfinance as yf

    fi = yf.Ticker(ticker).fast_info
    return float(fi.last_price), float(fi.previous_close)


class YFinancePrices:
    # Why: yfinance Yahoo'nun özel endpoint'ini kazır — resmî değil, kırılgan. Provenance'ta
    # bunu açıkça söylüyoruz ki kullanıcı hangi veriyle baktığını bilsin (spec §3).
    name = "yfinance (resmî değil)"

    def __init__(
        self,
        now: Callable[[], float] = time.time,
        fetch: Callable[[str], tuple[float, float]] = _yfinance_fetch,
    ) -> None:
        self._now = now
        self._fetch = fetch

    def quote(self, symbol: Symbol) -> Quote:
        try:
            last, prev = self._fetch(symbol.ticker)
        except (KeyError, TypeError) as e:
            # Why: yfinance bilinmeyen sembolde KeyError('exchangeTimezoneName')
            # (ya da None->float TypeError) fırlatır; temiz UnknownSymbol'e çevir.
            raise UnknownSymbol(symbol.ticker) from e
        return Quote(
            symbol=symbol,
            price=Money(Decimal(str(last)), "USD"),
            previous_close=Money(Decimal(str(prev)), "USD"),
            provenance=Provenance("yfinance", self._now()),
        )
```

- [ ] **Step 5: `market/us/__init__.py` — composer**

```python
"""US market plugin — ince composer. Yetenekleri kaynaklara dağıtır, domain VO'ya çevirir.
Hangi kaynağın hangi yeteneği doldurduğu buranın bilgisi; tool yüzeyine sızmaz.
"""

from sonar.domain.quote import Quote
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.us.prices import PriceSource, YFinancePrices


class USMarketPlugin(BaseMarketPlugin):
    market = "US"

    def __init__(self, prices: PriceSource | None = None) -> None:
        self._prices = prices or YFinancePrices()

    def get_quote(self, symbol: Symbol) -> Quote:
        return self._prices.quote(symbol)
```

- [ ] **Step 6: Geriye-uyum — mevcut testler kırılmasın**

`tests/test_us_plugin.py` ve `tests/test_quote_tool.py` bugün `USMarketPlugin(now=..., fetch=...)`
çağırıyor. Bu artık `YFinancePrices`'ın işi. **Testleri güncelle** (davranış aynı, kurulum değişti):

`tests/test_quote_tool.py` içinde `_registry()`:
```python
from sonar.market.us.prices import YFinancePrices

def _registry():
    reg = MarketRegistry()
    reg.register(USMarketPlugin(YFinancePrices(now=lambda: 1.0, fetch=lambda t: (110.0, 100.0))))
    return reg
```
Aynı düzeltmeyi `tests/test_us_plugin.py` ve `tests/test_agent_tool.py` içindeki `USMarketPlugin(...)`
çağrılarında da yap (`grep -rn "USMarketPlugin(" backend/tests` ile bul, hepsini çevir).

`sonar/api/app.py:24` içindeki `reg.register(USMarketPlugin())` **değişmez** (varsayılan yfinance).

- [ ] **Step 7: `market/us.py`'yi sil**

```bash
git rm backend/sonar/market/us.py
```

- [ ] **Step 8: Testleri koştur**

Run: `cd backend && uv run pytest -q`
Expected: PASS — mevcut 31 test + 2 yeni = 33 passed. Davranış değişmedi.

- [ ] **Step 9: Commit (yapısal — davranış değişmedi)**

```bash
git add -A backend/
git commit -m "refactor: market/us paket oldu; PriceSource Strategy + BaseMarketPlugin Unsupported varsayilani"
```

---

### Task A2: `market/sources/http.py` — rate-limitli HTTP istemcisi

**Files:**
- Create: `backend/sonar/market/sources/__init__.py`, `backend/sonar/market/sources/http.py`
- Test: `backend/tests/test_sources_http.py`

**Interfaces:**
- Produces: `HttpClient(user_agent: str, min_interval: float)` · `.get_json(url) -> dict` ·
  `.get_text(url) -> str` · `.get_bytes(url) -> bytes`

- [ ] **Step 1: Failing test — rate limit ve User-Agent**

`backend/tests/test_sources_http.py`:
```python
import httpx
import pytest
from sonar.market.sources.http import HttpClient


def test_sends_user_agent():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, json={"ok": True})

    client = HttpClient("Sonar/0.1 (test@example.com)", transport=httpx.MockTransport(handler))
    assert client.get_json("https://data.sec.gov/x") == {"ok": True}
    assert seen["ua"] == "Sonar/0.1 (test@example.com)"


def test_rate_limit_sleeps_between_calls():
    clock = {"t": 0.0}
    slept = []

    def handler(request):
        return httpx.Response(200, json={})

    client = HttpClient(
        "Sonar/0.1 (test@example.com)",
        min_interval=0.1,
        transport=httpx.MockTransport(handler),
        now=lambda: clock["t"],
        sleep=slept.append,
    )
    client.get_json("https://data.sec.gov/a")
    client.get_json("https://data.sec.gov/b")
    assert slept == [0.1]  # ikinci çağrı, aradan zaman geçmediği için bekledi


def test_http_error_propagates():
    client = HttpClient(
        "Sonar/0.1 (t@e.com)",
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
        retries=0,
    )
    with pytest.raises(httpx.HTTPStatusError):
        client.get_json("https://data.sec.gov/x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_sources_http.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.market.sources.http`

- [ ] **Step 3: Implement**

`backend/sonar/market/sources/http.py`:
```python
"""Market bilmeyen ortak HTTP makinesi: rate-limit + User-Agent + retry.

SEC EDGAR zorunlu tutuyor: gerçek iletişim bilgisi içeren User-Agent ve ≤10 req/s.
İhlal = IP ban. Bunu üç kaynak (EDGAR, FRED, FINRA) paylaşıyor → tek yerde (Rule of Three).
"""

import time
from typing import Callable

import httpx


class HttpClient:
    def __init__(
        self,
        user_agent: str,
        *,
        min_interval: float = 0.11,  # ~9 req/s — SEC'in 10 req/s sınırının altında
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval
        self._retries = retries
        self._now = now
        self._sleep = sleep
        self._last = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )

    def _throttle(self) -> None:
        wait = self._min_interval - (self._now() - self._last)
        if wait > 0:
            self._sleep(wait)
        self._last = self._now()

    def _get(self, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            self._throttle()
            try:
                resp = self._client.get(url)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.TransportError) as e:
                # Why: 429/5xx ve geçici ağ hataları retry'lanabilir; 4xx (404 gibi) değil.
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status is not None and status < 500 and status != 429:
                    raise
                last_error = e
                if attempt < self._retries:
                    self._sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def get_json(self, url: str) -> dict:
        return self._get(url).json()

    def get_text(self, url: str) -> str:
        return self._get(url).text

    def get_bytes(self, url: str) -> bytes:
        return self._get(url).content
```

`backend/sonar/market/sources/__init__.py`: boş dosya.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_sources_http.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/sonar/market/sources backend/tests/test_sources_http.py
git commit -m "feat: rate-limitli ortak HTTP istemcisi (EDGAR/FRED/FINRA paylasir)"
```

---

### Task A3: Alpaca fiyat kaynağı (Strategy'nin ikinci implementasyonu)

**Files:**
- Modify: `backend/sonar/market/us/prices.py`, `backend/sonar/market/us/__init__.py`,
  `backend/sonar/api/app.py:22-26`, `backend/sonar/config.py`
- Test: `backend/tests/test_prices.py`

**Interfaces:**
- Consumes: `HttpClient` (A2), `PriceSource` (A1)
- Produces: `AlpacaPrices(key, secret, http)` · `make_price_source() -> PriceSource` (env'e bakar)

- [ ] **Step 1: Failing test**

`backend/tests/test_prices.py`:
```python
import httpx
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.us.prices import AlpacaPrices, YFinancePrices, make_price_source

SNAPSHOT = {
    "latestTrade": {"p": 180.42},
    "prevDailyBar": {"c": 175.00},
}


def _alpaca(monkeypatch=None):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=SNAPSHOT))
    http = HttpClient("Sonar/0.1 (t@e.com)", transport=transport, min_interval=0)
    return AlpacaPrices(key="k", secret="s", http=http, now=lambda: 7.0)


def test_alpaca_quote_uses_snapshot():
    q = _alpaca().quote(Symbol("NVDA", "US"))
    assert str(q.price.amount) == "180.42"
    assert str(q.previous_close.amount) == "175.0"
    assert q.provenance.source == "alpaca"
    assert round(q.change_pct, 2) == 3.1


def test_make_price_source_without_key_falls_back_to_yfinance(monkeypatch):
    monkeypatch.delenv("SONAR_ALPACA_KEY", raising=False)
    assert isinstance(make_price_source(), YFinancePrices)


def test_make_price_source_with_key_uses_alpaca(monkeypatch):
    monkeypatch.setenv("SONAR_ALPACA_KEY", "k")
    monkeypatch.setenv("SONAR_ALPACA_SECRET", "s")
    assert isinstance(make_price_source(), AlpacaPrices)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_prices.py -v`
Expected: FAIL — `ImportError: cannot import name 'AlpacaPrices'`

- [ ] **Step 3: Implement — `prices.py` sonuna ekle**

```python
import os

ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks"


class AlpacaPrices:
    """Resmî, sözleşmeli fiyat API'si. Tek snapshot çağrısı = son işlem + önceki günün kapanışı."""

    name = "alpaca"

    def __init__(
        self,
        *,
        key: str,
        secret: str,
        http: HttpClient | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._now = now
        self._http = http or HttpClient(
            f"Sonar/0.1 ({os.environ.get('SONAR_CONTACT', 'sonar@localhost')})",
            min_interval=0.3,  # Alpaca ücretsiz katman: 200 req/dk
        )
        self._http._client.headers.update(
            {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        )

    def quote(self, symbol: Symbol) -> Quote:
        data = self._http.get_json(f"{ALPACA_DATA_URL}/{symbol.ticker}/snapshot")
        trade = data.get("latestTrade") or {}
        prev = data.get("prevDailyBar") or {}
        if "p" not in trade or "c" not in prev:
            raise UnknownSymbol(symbol.ticker)
        return Quote(
            symbol=symbol,
            price=Money(Decimal(str(trade["p"])), "USD"),
            previous_close=Money(Decimal(str(prev["c"])), "USD"),
            provenance=Provenance("alpaca", self._now()),
        )


def make_price_source() -> PriceSource:
    """Strategy seçimi: key varsa Alpaca (resmî), yoksa yfinance (kırılgan, Provenance söyler)."""
    key = os.environ.get("SONAR_ALPACA_KEY")
    secret = os.environ.get("SONAR_ALPACA_SECRET")
    if key and secret:
        return AlpacaPrices(key=key, secret=secret)
    return YFinancePrices()
```

Dosyanın başındaki import'lara `from sonar.market.sources.http import HttpClient` ekle.

- [ ] **Step 4: `api/app.py` — plugin'i env'e göre kur**

`_default_registry()`'yi değiştir (satır 22-26):
```python
def _default_registry() -> MarketRegistry:
    from sonar.market.us.prices import make_price_source

    reg = MarketRegistry()
    reg.register(USMarketPlugin(make_price_source()))
    return reg
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 36 passed

- [ ] **Step 6: Slow test — gerçek Alpaca (opsiyonel, key varsa)**

`backend/tests/test_prices.py` sonuna:
```python
import os
import pytest


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("SONAR_ALPACA_KEY"), reason="Alpaca key yok")
def test_alpaca_real_quote():
    src = AlpacaPrices(
        key=os.environ["SONAR_ALPACA_KEY"], secret=os.environ["SONAR_ALPACA_SECRET"]
    )
    q = src.quote(Symbol("AAPL", "US"))
    assert q.price.amount > 0
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: Alpaca fiyat kaynagi (Strategy) — key yoksa yfinance fallback"
```

---

### Task A4: OHLCV — domain VO + PriceSource.bars + `tools/_cache.py` + `get_ohlcv`

**Files:**
- Create: `backend/sonar/domain/candle.py`, `backend/sonar/tools/_cache.py`, `backend/sonar/tools/ohlcv.py`
- Modify: `backend/sonar/market/us/prices.py`, `backend/sonar/market/us/__init__.py`,
  `backend/sonar/market/base.py`, `backend/sonar/config.py`
- Test: `backend/tests/test_ohlcv.py`

**Interfaces:**
- Produces: `Candle(ts, open, high, low, close, volume)` · `OhlcvSeries(symbol, interval, candles, provenance)` ·
  `cached(cache, key, ttl, fn) -> dict` · `get_ohlcv(ticker, range_, interval, *, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test**

`backend/tests/test_ohlcv.py`:
```python
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.ohlcv import get_ohlcv

CANDLES = [
    Candle(ts=1, open=10.0, high=11.0, low=9.0, close=10.5, volume=1000),
    Candle(ts=2, open=10.5, high=12.0, low=10.0, close=11.5, volume=2000),
]


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def __init__(self):
        self.calls = 0

    def get_ohlcv(self, symbol, range_, interval):
        self.calls += 1
        return OhlcvSeries(
            symbol=symbol, interval=interval, candles=CANDLES,
            provenance=Provenance("fake", 1.0),
        )


def _reg(plugin):
    reg = MarketRegistry()
    reg.register(plugin)
    return reg


def test_get_ohlcv_returns_serialisable_candles(conn):
    out = get_ohlcv("nvda", "6mo", "1d", registry=_reg(FakeMarket()), cache=Cache(conn), ttl=60)
    assert out["ticker"] == "NVDA"
    assert out["source"] == "fake"
    assert out["candles"][1] == {
        "ts": 2, "open": 10.5, "high": 12.0, "low": 10.0, "close": 11.5, "volume": 2000
    }


def test_get_ohlcv_second_call_hits_cache(conn):
    plugin = FakeMarket()
    cache = Cache(conn, now=lambda: 1.0)
    get_ohlcv("NVDA", "6mo", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    get_ohlcv("NVDA", "6mo", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    assert plugin.calls == 1


def test_cache_key_varies_by_range(conn):
    plugin = FakeMarket()
    cache = Cache(conn, now=lambda: 1.0)
    get_ohlcv("NVDA", "6mo", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    get_ohlcv("NVDA", "1y", "1d", registry=_reg(plugin), cache=cache, ttl=900)
    assert plugin.calls == 2  # farklı range = farklı cache anahtarı
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_ohlcv.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.domain.candle`

- [ ] **Step 3: `domain/candle.py`**

```python
from dataclasses import dataclass

from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Candle:
    ts: int          # unix saniye, bar açılışı
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class OhlcvSeries:
    symbol: Symbol
    interval: str    # "1d" | "1h" | "5m"
    candles: list[Candle]
    provenance: Provenance
```

- [ ] **Step 4: `tools/_cache.py` — 11 tool'un ortak sarmalı**

```python
"""Tool'ların cache sarmalı tek yerde. Bu olmadan her tool aynı 6 satırı tekrar ederdi
(Duplicated Code — Fowler). Tool'un işi: anahtarı ve hesabı vermek."""

import json
from typing import Callable

from sonar.store.cache import Cache


def cached(cache: Cache, key: str, ttl: int, compute: Callable[[], dict]) -> dict:
    hit = cache.get(key)
    if hit is not None:
        return json.loads(hit)
    out = compute()
    cache.set(key, json.dumps(out), ttl)
    return out
```

- [ ] **Step 5: `tools/ohlcv.py`**

```python
from dataclasses import asdict

from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_ohlcv(
    ticker: str,
    range_: str = "6mo",
    interval: str = "1d",
    *,
    registry: MarketRegistry,
    cache: Cache,
    ttl: int,
    market: str = "US",
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        series = registry.get(symbol.market).get_ohlcv(symbol, range_, interval)
        return {
            "ticker": symbol.ticker,
            "interval": series.interval,
            "candles": [asdict(c) for c in series.candles],
            "source": series.provenance.source,
        }

    return cached(cache, f"ohlcv:{symbol.market}:{symbol.ticker}:{range_}:{interval}", ttl, compute)
```

- [ ] **Step 6: `PriceSource.bars` + iki implementasyon**

`market/us/prices.py` — Protocol'e ekle:
```python
class PriceSource(Protocol):
    name: str

    def quote(self, symbol: Symbol) -> Quote: ...
    def bars(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries: ...
```

`YFinancePrices.bars`:
```python
    def bars(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        import yfinance as yf

        df = yf.Ticker(symbol.ticker).history(period=range_, interval=interval)
        if df.empty:
            raise UnknownSymbol(symbol.ticker)
        candles = [
            Candle(
                ts=int(idx.timestamp()),
                open=float(row.Open), high=float(row.High), low=float(row.Low),
                close=float(row.Close), volume=int(row.Volume),
            )
            for idx, row in df.iterrows()
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("yfinance", self._now()))
```

`AlpacaPrices.bars`:
```python
    _TIMEFRAME = {"1d": "1Day", "1h": "1Hour", "5m": "5Min"}
    _RANGE_DAYS = {"1mo": 31, "3mo": 93, "6mo": 186, "1y": 366, "2y": 731, "5y": 1827}

    def bars(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        from datetime import datetime, timedelta, timezone

        tf = self._TIMEFRAME.get(interval)
        days = self._RANGE_DAYS.get(range_)
        if tf is None or days is None:
            raise ValueError(f"desteklenmeyen range/interval: {range_}/{interval}")
        start = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        url = (
            f"{ALPACA_DATA_URL}/{symbol.ticker}/bars"
            f"?timeframe={tf}&start={start}&limit=10000&adjustment=split"
        )
        data = self._http.get_json(url)
        bars = data.get("bars") or []
        if not bars:
            raise UnknownSymbol(symbol.ticker)
        candles = [
            Candle(
                ts=int(datetime.fromisoformat(b["t"].replace("Z", "+00:00")).timestamp()),
                open=b["o"], high=b["h"], low=b["l"], close=b["c"], volume=int(b["v"]),
            )
            for b in bars
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("alpaca", self._now()))
```

`market/us/__init__.py`:
```python
    def get_ohlcv(self, symbol: Symbol, range_: str, interval: str) -> OhlcvSeries:
        return self._prices.bars(symbol, range_, interval)
```

- [ ] **Step 7: `config.py` — yeni TTL'ler**

```python
QUOTE_TTL_SECONDS = 60
OHLCV_TTL_SECONDS = 900          # 15 dk (gün-içi bar)
FUNDAMENTALS_TTL_SECONDS = 86400  # 24 sa — çeyreklik veri
NEWS_TTL_SECONDS = 900
MACRO_TTL_SECONDS = 21600         # 6 sa
PEERS_TTL_SECONDS = 86400
```

- [ ] **Step 8: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 39 passed

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: get_ohlcv — Candle/OhlcvSeries VO + PriceSource.bars + tools/_cache helper"
```

---

### Task A5: `analytics/indicators.py` — göstergeler **elle** (referans değerlerle test)

Kütüphane yok (ADR-0006). Testler **elle hesaplanmış** referanslara karşı — kendi kodumuzun çıktısını
kendi kodumuzla doğrulamak değersizdir.

**Files:**
- Create: `backend/sonar/analytics/__init__.py`, `backend/sonar/analytics/indicators.py`
- Modify: `backend/pyproject.toml` (pandas/numpy beyanı), `backend/tests/test_layering.py`
- Test: `backend/tests/test_indicators.py`

**Interfaces:**
- Produces: `rsi(closes, period=14) -> float` · `ema(values, period) -> float` ·
  `macd(closes) -> dict{macd, signal, histogram}` · `bollinger(closes, period=20, k=2) -> dict{upper, mid, lower}` ·
  `support_resistance(candles, lookback=60) -> dict{support, resistance}` · `obv(candles) -> float` ·
  `volume_anomaly(candles, window=20) -> float`

- [ ] **Step 1: Failing test — referans değerler**

`backend/tests/test_indicators.py`:
```python
import pytest
from sonar.analytics.indicators import (
    bollinger, ema, macd, obv, rsi, support_resistance, volume_anomaly,
)
from sonar.domain.candle import Candle

# Wilder'ın orijinal RSI örneği (New Concepts in Technical Trading Systems, 1978).
# 14 periyotluk ilk RSI değeri kaynakta 70.53 olarak verilir.
WILDER = [
    44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
    45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
]


def test_rsi_matches_wilder_reference():
    assert rsi(WILDER, period=14) == pytest.approx(70.53, abs=0.05)


def test_rsi_all_gains_is_100():
    assert rsi([float(i) for i in range(1, 20)], period=14) == pytest.approx(100.0)


def test_rsi_needs_enough_data():
    with pytest.raises(ValueError, match="yetersiz veri"):
        rsi([1.0, 2.0], period=14)


def test_ema_matches_hand_calculation():
    # EMA(3): ilk değer = SMA(3) = 2.0; k = 2/(3+1) = 0.5
    # 4 → 2.0 + 0.5*(4-2.0) = 3.0 ; 5 → 3.0 + 0.5*(5-3.0) = 4.0
    assert ema([1.0, 2.0, 3.0, 4.0, 5.0], period=3) == pytest.approx(4.0)


def test_bollinger_matches_hand_calculation():
    # 5 eşit değer → std = 0 → üç bant da aynı
    out = bollinger([10.0] * 20, period=20, k=2)
    assert out["mid"] == pytest.approx(10.0)
    assert out["upper"] == pytest.approx(10.0)
    assert out["lower"] == pytest.approx(10.0)


def test_bollinger_two_sigma():
    values = [8.0, 12.0] * 10  # ortalama 10, nüfus std = 2
    out = bollinger(values, period=20, k=2)
    assert out["mid"] == pytest.approx(10.0)
    assert out["upper"] == pytest.approx(14.0)
    assert out["lower"] == pytest.approx(6.0)


def test_macd_zero_when_flat():
    out = macd([10.0] * 40)
    assert out["macd"] == pytest.approx(0.0, abs=1e-9)
    assert out["histogram"] == pytest.approx(0.0, abs=1e-9)


def _c(close: float, volume: int = 100) -> Candle:
    return Candle(ts=0, open=close, high=close + 1, low=close - 1, close=close, volume=volume)


def test_support_resistance_uses_window_extremes():
    candles = [_c(10.0), _c(20.0), _c(15.0)]
    out = support_resistance(candles, lookback=3)
    assert out["support"] == pytest.approx(9.0)     # en düşük low
    assert out["resistance"] == pytest.approx(21.0)  # en yüksek high


def test_obv_accumulates_on_up_days():
    # 10 → 11 (yukarı, +200) → 10 (aşağı, -300)
    candles = [_c(10.0, 100), _c(11.0, 200), _c(10.0, 300)]
    assert obv(candles) == pytest.approx(-100.0)


def test_volume_anomaly_ratio():
    candles = [_c(10.0, 100)] * 20 + [_c(10.0, 250)]
    assert volume_anomaly(candles, window=20) == pytest.approx(2.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_indicators.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.analytics`

- [ ] **Step 3: Implement**

`backend/sonar/analytics/indicators.py`:
```python
"""Teknik göstergeler — elle yazılır (ADR-0006: TA-Lib/pandas-ta yok).

Saf: I/O yok, market bilmez. Her market için aynı matematik → çekirdekte, plugin'de değil.
"""

import numpy as np

from sonar.domain.candle import Candle


def _need(values: list[float], n: int) -> None:
    if len(values) < n:
        raise ValueError(f"yetersiz veri: {len(values)} < {n}")


def rsi(closes: list[float], period: int = 14) -> float:
    """Wilder RSI. İlk ortalama = basit ortalama, sonrası Wilder yumuşatması."""
    _need(closes, period + 1)
    deltas = np.diff(np.asarray(closes, dtype=float))
    gains = np.clip(deltas, 0, None)
    losses = -np.clip(deltas, None, 0)
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    for g, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def ema(values: list[float], period: int) -> float:
    """Son EMA değeri. Tohum = ilk `period` değerin SMA'sı."""
    _need(values, period)
    k = 2 / (period + 1)
    out = float(np.mean(values[:period]))
    for v in values[period:]:
        out = v * k + out * (1 - k)
    return out


def _ema_series(values: list[float], period: int) -> list[float]:
    _need(values, period)
    k = 2 / (period + 1)
    out = [float(np.mean(values[:period]))]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    _need(closes, slow + signal)
    fast_s = _ema_series(closes, fast)
    slow_s = _ema_series(closes, slow)
    # Why: iki seri farklı uzunlukta başlar (fast daha erken tohumlanır) → kuyruktan hizala.
    n = min(len(fast_s), len(slow_s))
    line = [f - s for f, s in zip(fast_s[-n:], slow_s[-n:])]
    signal_line = _ema_series(line, signal)
    return {
        "macd": round(line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(line[-1] - signal_line[-1], 4),
    }


def bollinger(closes: list[float], period: int = 20, k: float = 2.0) -> dict:
    _need(closes, period)
    window = np.asarray(closes[-period:], dtype=float)
    mid = float(window.mean())
    sd = float(window.std())  # nüfus std (ddof=0) — Bollinger'ın orijinal tanımı
    return {
        "mid": round(mid, 4),
        "upper": round(mid + k * sd, 4),
        "lower": round(mid - k * sd, 4),
    }


def support_resistance(candles: list[Candle], lookback: int = 60) -> dict:
    """En basit ve dürüst tanım: pencere içindeki uç noktalar.
    ponytail: pivot/fractal algoritmasına ancak bu yetersiz kalırsa geçilir."""
    if not candles:
        raise ValueError("yetersiz veri: 0 mum")
    window = candles[-lookback:]
    return {
        "support": round(min(c.low for c in window), 4),
        "resistance": round(max(c.high for c in window), 4),
    }


def obv(candles: list[Candle]) -> float:
    """On-Balance Volume: kapanış yükseldiyse hacim eklenir, düştüyse çıkarılır."""
    _need(candles, 2)
    total = 0.0
    for prev, cur in zip(candles, candles[1:]):
        if cur.close > prev.close:
            total += cur.volume
        elif cur.close < prev.close:
            total -= cur.volume
    return total


def volume_anomaly(candles: list[Candle], window: int = 20) -> float:
    """Son barın hacmi / önceki `window` barın ortalaması. 1.0 = normal, 2.5 = 2.5 katı."""
    _need(candles, window + 1)
    baseline = float(np.mean([c.volume for c in candles[-window - 1 : -1]]))
    if baseline == 0:
        return 0.0
    return round(candles[-1].volume / baseline, 2)
```

`backend/sonar/analytics/__init__.py`: boş.

- [ ] **Step 4: `pyproject.toml` — pandas/numpy'ı açıkça beyan et**

`dependencies` listesine ekle (yfinance zaten transitif getiriyor; import ediyorsak beyan ederiz):
```toml
  "numpy>=1.26",
  "pandas>=2.2",
```
Sonra: `cd backend && uv sync`

- [ ] **Step 5: `test_layering.py` — `analytics` de provider-free olsun**

`PROVIDER_FREE_DIRS` satırını değiştir:
```python
PROVIDER_FREE_DIRS = ["api", "tools", "domain", "store", "market", "analytics"]
```

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 50 passed

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: analytics/indicators — RSI/EMA/MACD/BB/S-R/OBV/hacim anomalisi (elle, Wilder referansli test)"
```

---

### Task A6: `tools/technicals.py` — plugin'e dokunmayan tool

Bu tool **market plugin'ini hiç çağırmaz**: OHLCV'yi `get_ohlcv` üzerinden alır, hesabı `analytics`'te yapar.
TR plugin'i geldiğinde bu dosya tek satır değişmez — kat ayrımının somut sınaması.

**Files:**
- Create: `backend/sonar/tools/technicals.py`
- Test: `backend/tests/test_technicals_tool.py`

**Interfaces:**
- Consumes: `get_ohlcv` (A4), `analytics.indicators` (A5)
- Produces: `get_technicals(ticker, *, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test**

`backend/tests/test_technicals_tool.py`:
```python
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.technicals import get_technicals


def _candles(n=60):
    return [
        Candle(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
        for i in range(n)
    ]


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        return OhlcvSeries(symbol, interval, _candles(), Provenance("fake", 1.0))


def _reg():
    reg = MarketRegistry()
    reg.register(FakeMarket())
    return reg


def test_technicals_returns_computed_indicators(conn):
    out = get_technicals("nvda", registry=_reg(), cache=Cache(conn), ttl=900)
    assert out["ticker"] == "NVDA"
    assert out["rsi"] == 100.0            # sürekli yükselen seri
    assert out["macd"]["macd"] > 0
    assert out["support"] < out["resistance"]
    assert out["volume_anomaly"] == 1.0   # sabit hacim
    assert "obv" in out and "bollinger" in out and "ema50" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_technicals_tool.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.tools.technicals`

- [ ] **Step 3: Implement**

```python
"""Teknik gösterge tool'u — market plugin'ine DOKUNMAZ.
OHLCV'yi tool katmanından alır, hesabı analytics'te yapar (ADR-0003: sayı çekirdekte).
"""

from sonar.analytics import indicators
from sonar.domain.candle import Candle
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached
from sonar.tools.ohlcv import get_ohlcv


def get_technicals(
    ticker: str,
    *,
    registry: MarketRegistry,
    cache: Cache,
    ttl: int,
    market: str = "US",
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        raw = get_ohlcv(
            symbol.ticker, "1y", "1d",
            registry=registry, cache=cache, ttl=ttl, market=market,
        )
        candles = [Candle(**c) for c in raw["candles"]]
        closes = [c.close for c in candles]
        sr = indicators.support_resistance(candles)
        return {
            "ticker": symbol.ticker,
            "rsi": round(indicators.rsi(closes), 2),
            "macd": indicators.macd(closes),
            "bollinger": indicators.bollinger(closes),
            "ema50": round(indicators.ema(closes, 50), 2),
            "ema200": round(indicators.ema(closes, 200), 2) if len(closes) >= 200 else None,
            "support": sr["support"],
            "resistance": sr["resistance"],
            "obv": indicators.obv(candles),
            "volume_anomaly": indicators.volume_anomaly(candles),
            "source": raw["source"],
        }

    return cached(cache, f"technicals:{symbol.market}:{symbol.ticker}", ttl, compute)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 51 passed

- [ ] **Step 5: Commit**

```bash
git add backend/sonar/tools/technicals.py backend/tests/test_technicals_tool.py
git commit -m "feat: get_technicals — plugin'e dokunmadan OHLCV uzerinden hesap"
```
