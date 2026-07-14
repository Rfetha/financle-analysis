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
| `defusedxml>=0.7` | **uzaktan** XML parse (RSS, Form 4) — stdlib ElementTree XXE/billion-laughs'a açık | backend |
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

---

### Task A7: EDGAR — ticker↔CIK + companyfacts → `get_fundamentals`

SEC'in resmî XBRL verisi. Bu task'ta kurulan `EdgarClient` (CIK haritası + rate-limitli erişim)
**Faz B'nin 13F/Form 4 tabanı** — bir kez kurulur, üç kez kullanılır.

**Files:**
- Create: `backend/sonar/domain/fundamentals.py`, `backend/sonar/market/us/edgar.py`,
  `backend/sonar/tools/fundamentals.py`
- Modify: `backend/sonar/market/us/__init__.py`, `backend/sonar/config.py`
- Test: `backend/tests/test_edgar.py`, `backend/tests/test_fundamentals_tool.py`

**Interfaces:**
- Consumes: `HttpClient` (A2)
- Produces: `EdgarClient(http)` · `.cik_for(ticker) -> str` (10 hane, sıfır dolgulu) ·
  `.company_facts(cik) -> dict` · `.fundamentals(symbol) -> Fundamentals` ·
  `Fundamentals(symbol, revenue, net_income, gross_margin, net_margin, revenue_growth_yoy, eps, pe, debt_to_equity, period, provenance)` ·
  `get_fundamentals(ticker, *, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test — CIK haritası ve XBRL kavram çıkarımı**

`backend/tests/test_edgar.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_edgar.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.market.us.edgar`

- [ ] **Step 3: `domain/fundamentals.py`**

```python
from dataclasses import dataclass

from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Fundamentals:
    symbol: Symbol
    period: str                      # "FY2026"
    revenue: float | None
    net_income: float | None
    net_margin: float | None         # %
    revenue_growth_yoy: float | None  # %
    provenance: Provenance
```

> Değerleme çarpanları (P/E) burada **yok**: EDGAR fiyat vermez. P/E, tool katmanında fiyat × EPS ile
> hesaplanır — kaynak ayrımı VO'ya sızmasın diye Fundamentals saf muhasebe verisi kalır.

- [ ] **Step 4: `market/us/edgar.py`**

```python
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
```

- [ ] **Step 5: `tools/fundamentals.py`**

```python
from dataclasses import asdict

from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_fundamentals(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        f = registry.get(symbol.market).get_fundamentals(symbol)
        out = asdict(f)
        out["ticker"] = symbol.ticker
        out["source"] = f.provenance.source
        out.pop("symbol")
        out.pop("provenance")
        return out

    return cached(cache, f"fundamentals:{symbol.market}:{symbol.ticker}", ttl, compute)
```

- [ ] **Step 6: Plugin'e bağla — `market/us/__init__.py`**

```python
import os

from sonar.market.sources.http import HttpClient
from sonar.market.us.edgar import EdgarClient


def _default_http() -> HttpClient:
    contact = os.environ.get("SONAR_CONTACT", "sonar@localhost")
    return HttpClient(f"Sonar/0.1 ({contact})")


class USMarketPlugin(BaseMarketPlugin):
    market = "US"

    def __init__(self, prices: PriceSource | None = None, edgar: EdgarClient | None = None) -> None:
        self._prices = prices or YFinancePrices()
        self._edgar = edgar or EdgarClient(_default_http())

    def get_fundamentals(self, symbol: Symbol) -> Fundamentals:
        return self._edgar.fundamentals(symbol)
```

- [ ] **Step 7: Tool testi**

`backend/tests/test_fundamentals_tool.py`:
```python
from sonar.domain.fundamentals import Fundamentals
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.fundamentals import get_fundamentals


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_fundamentals(self, symbol):
        return Fundamentals(
            symbol=symbol, period="FY2026", revenue=150.0, net_income=30.0,
            net_margin=20.0, revenue_growth_yoy=50.0,
            provenance=Provenance("SEC EDGAR companyfacts", 1.0),
        )


def test_fundamentals_tool_shape(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    out = get_fundamentals("nvda", registry=reg, cache=Cache(conn), ttl=86400)
    assert out == {
        "ticker": "NVDA", "period": "FY2026", "revenue": 150.0, "net_income": 30.0,
        "net_margin": 20.0, "revenue_growth_yoy": 50.0, "source": "SEC EDGAR companyfacts",
    }
```

- [ ] **Step 8: Slow test — gerçek EDGAR**

`backend/tests/test_edgar.py` sonuna:
```python
@pytest.mark.slow
def test_real_edgar_fundamentals():
    from sonar.market.us import _default_http

    client = EdgarClient(_default_http())
    f = client.fundamentals(Symbol("AAPL", "US"))
    assert f.revenue and f.revenue > 1e11  # Apple yıllık geliri 100B$ üstü
```

- [ ] **Step 9: Run tests**

Run: `cd backend && uv run pytest -q && uv run pytest -m slow -q -k edgar`
Expected: 56 passed · slow: 1 passed

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "feat: EDGAR istemcisi (ticker<->CIK + companyfacts) + get_fundamentals"
```

---

### Task A8: `get_peers` — EDGAR SIC koduyla sektör eşlikçileri

**Files:**
- Modify: `backend/sonar/market/us/edgar.py`, `backend/sonar/market/us/__init__.py`
- Create: `backend/sonar/tools/peers.py`
- Test: `backend/tests/test_peers.py`

**Interfaces:**
- Consumes: `EdgarClient` (A7)
- Produces: `EdgarClient.sic_for(symbol) -> tuple[str, str]` (kod, tanım) · `EdgarClient.peers(symbol) -> list[str]` ·
  `get_peers(ticker, *, registry, cache, ttl) -> dict{ticker, sic, sic_description, peers, source}`

- [ ] **Step 1: Failing test**

`backend/tests/test_peers.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_peers.py -v`
Expected: FAIL — `AttributeError: 'EdgarClient' object has no attribute 'sic_for'`

- [ ] **Step 3: `edgar.py`'ye ekle**

```python
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
```

> **Uyarı (plan yazarı → uygulayıcı):** bu naif tarama gerçek EDGAR'da **yavaş** (10 req/s sınırı,
> binlerce ticker). Step 5'te ölçeceğiz; 5 saniyeyi aşarsa aynı task içinde **SIC tablosunu bir kez
> indirip cache'e yazan** yola geçilir (`store` içinde `sic(ticker, sic_code)` tablosu, ilk çağrıda
> doldurulur). Karar ölçümle verilir, tahminle değil.

- [ ] **Step 4: `tools/peers.py`**

```python
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_peers(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        return {
            "ticker": symbol.ticker,
            "peers": registry.get(symbol.market).get_peers(symbol),
            "source": "SEC EDGAR SIC",
        }

    return cached(cache, f"peers:{symbol.market}:{symbol.ticker}", ttl, compute)
```

`market/us/__init__.py`:
```python
    def get_peers(self, symbol: Symbol) -> list[str]:
        return self._edgar.peers(symbol)
```

- [ ] **Step 5: Ölç — gerçek EDGAR'da süre**

`backend/tests/test_peers.py` sonuna:
```python
import time
import pytest


@pytest.mark.slow
def test_real_peers_under_5_seconds():
    from sonar.market.us import _default_http

    client = EdgarClient(_default_http())
    started = time.perf_counter()
    peers = client.peers(Symbol("NVDA", "US"))
    elapsed = time.perf_counter() - started
    assert peers, "peers boş döndü"
    assert elapsed < 5.0, f"peers {elapsed:.1f}s sürdü — SIC tablosunu cache'lemeye geç"
```

Run: `cd backend && uv run pytest -m slow -q -k peers`
Expected: PASS. **FAIL ederse** (5sn'yi aştıysa) yukarıdaki uyarıdaki cache'li yola geç ve testi
tekrar koştur — task bitmeden.

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 58 passed

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: get_peers — EDGAR SIC kodu uzerinden sektor eslikcileri"
```

---

### Task A9: `get_news` — RSS (ortak parser + US feed listesi)

**Files:**
- Create: `backend/sonar/domain/news.py`, `backend/sonar/market/sources/rss.py`,
  `backend/sonar/market/us/news.py`, `backend/sonar/tools/news.py`
- Modify: `backend/sonar/market/us/__init__.py`, `backend/pyproject.toml` (`defusedxml>=0.7` ekle,
  sonra `uv sync`)
- Test: `backend/tests/test_news.py`

**Interfaces:**
- Produces: `NewsItem(title, url, source, published_at)` · `parse_rss(xml, source) -> list[NewsItem]` ·
  `USNews(http).for_symbol(symbol) -> list[NewsItem]` · `get_news(ticker, *, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test**

`backend/tests/test_news.py`:
```python
import httpx
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.sources.rss import parse_rss
from sonar.market.us.news import USNews

FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>NVIDIA beats estimates</title>
    <link>https://example.com/a</link>
    <pubDate>Mon, 13 Jul 2026 14:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Chip demand rises</title>
    <link>https://example.com/b</link>
    <pubDate>Mon, 13 Jul 2026 09:00:00 GMT</pubDate>
  </item>
</channel></rss>"""


def test_parse_rss_extracts_items():
    items = parse_rss(FEED, source="Yahoo Finance")
    assert len(items) == 2
    assert items[0].title == "NVIDIA beats estimates"
    assert items[0].url == "https://example.com/a"
    assert items[0].source == "Yahoo Finance"
    assert items[0].published_at == 1784023200  # 2026-07-13 14:00 UTC


def test_parse_rss_tolerates_missing_date():
    xml = "<rss><channel><item><title>T</title><link>u</link></item></channel></rss>"
    items = parse_rss(xml, source="X")
    assert items[0].published_at is None


def test_us_news_fetches_and_sorts_newest_first():
    http = HttpClient(
        "Sonar/0.1 (t@e.com)", min_interval=0,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=FEED)),
    )
    items = USNews(http).for_symbol(Symbol("NVDA", "US"))
    assert [i.title for i in items][:1] == ["NVIDIA beats estimates"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_news.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.market.sources.rss`

- [ ] **Step 3: `domain/news.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: int | None  # unix saniye
```

- [ ] **Step 4: `market/sources/rss.py` — ortak parser (stdlib)**

```python
"""RSS → NewsItem. Market bilmez; feed URL'lerini plugin verir.

ponytail: feedparser bağımlılığı eklemiyoruz — email.utils + XML parse yetiyor.

Why defusedxml: bu XML *uzaktan* geliyor (güven sınırı). Stdlib ElementTree XXE ve
billion-laughs saldırılarına açık; defusedxml aynı API'yi güvenli haliyle verir.
Aynı gerekçe Faz B'deki Form 4 XML parse'ı için de geçerli.
"""

from email.utils import parsedate_to_datetime

from defusedxml import ElementTree

from sonar.domain.news import NewsItem


def _timestamp(text: str | None) -> int | None:
    if not text:
        return None
    try:
        return int(parsedate_to_datetime(text).timestamp())
    except (TypeError, ValueError):
        return None


def parse_rss(xml: str, source: str) -> list[NewsItem]:
    root = ElementTree.fromstring(xml)
    items = []
    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        url = (node.findtext("link") or "").strip()
        if not title or not url:
            continue
        items.append(
            NewsItem(
                title=title,
                url=url,
                source=source,
                published_at=_timestamp(node.findtext("pubDate")),
            )
        )
    return items
```

- [ ] **Step 5: `market/us/news.py`**

```python
"""US haber kaynakları. Feed listesi burada (market bilgisi), parse ortakta."""

from sonar.domain.news import NewsItem
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.sources.rss import parse_rss

YAHOO_FEED = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


class USNews:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def for_symbol(self, symbol: Symbol, limit: int = 10) -> list[NewsItem]:
        xml = self._http.get_text(YAHOO_FEED.format(ticker=symbol.ticker))
        items = parse_rss(xml, source="Yahoo Finance")
        items.sort(key=lambda i: i.published_at or 0, reverse=True)
        return items[:limit]
```

- [ ] **Step 6: `tools/news.py` + plugin bağlantısı**

```python
from dataclasses import asdict

from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_news(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        items = registry.get(symbol.market).get_news(symbol)
        return {"ticker": symbol.ticker, "items": [asdict(i) for i in items]}

    return cached(cache, f"news:{symbol.market}:{symbol.ticker}", ttl, compute)
```

`market/us/__init__.py`:
```python
    def __init__(self, prices=None, edgar=None, news=None) -> None:
        http = _default_http()
        self._prices = prices or YFinancePrices()
        self._edgar = edgar or EdgarClient(http)
        self._news = news or USNews(http)

    def get_news(self, symbol: Symbol) -> list[NewsItem]:
        return self._news.for_symbol(symbol)
```

- [ ] **Step 7: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 61 passed

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: get_news — ortak RSS parser (stdlib) + US feed listesi"
```

---

### Task A10: `get_macro_snapshot` — FRED (key'siz) + GlobalMacro

**GlobalMacro fiyat kaynağına bağlanmaz:** Alpaca yalnız ABD hissesi verir; VIX/DXY/petrol orada yok.
Hepsi FRED'de var (`VIXCLS`, `DTWEXBGS`, `DCOILWTICO`) → tek kaynak, key yok, ters bağımlılık yok.

**Files:**
- Create: `backend/sonar/domain/macro.py`, `backend/sonar/market/sources/fred.py`,
  `backend/sonar/market/sources/global_macro.py`, `backend/sonar/market/us/macro.py`,
  `backend/sonar/tools/macro.py`
- Modify: `backend/sonar/market/us/__init__.py`
- Test: `backend/tests/test_macro.py`

**Interfaces:**
- Produces: `FredClient(http).latest(series_ids) -> dict[str, float]` ·
  `GlobalMacro(fred).snapshot() -> GlobalSnapshot(vix, dxy, wti)` ·
  `USMacro(fred).snapshot() -> LocalSnapshot(fed_funds, cpi_yoy, yield_10y, yield_2y, curve_10y_2y)` ·
  `MacroSnapshot(global_, local, provenance)` · `get_macro_snapshot(*, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test**

`backend/tests/test_macro.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_macro.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.market.sources.fred`

- [ ] **Step 3: `domain/macro.py`**

```python
from dataclasses import dataclass

from sonar.domain.quote import Provenance


@dataclass(frozen=True, slots=True)
class GlobalSnapshot:
    """Ülkeden bağımsız rejim: oynaklık, dolar, emtia. Her market kullanır."""
    vix: float | None
    dxy: float | None
    wti: float | None


@dataclass(frozen=True, slots=True)
class LocalSnapshot:
    """Market'in ülkesine özel: politika faizi, enflasyon, getiri eğrisi."""
    fed_funds: float | None
    cpi_yoy: float | None
    yield_10y: float | None
    yield_2y: float | None
    curve_10y_2y: float | None


@dataclass(frozen=True, slots=True)
class MacroSnapshot:
    global_: GlobalSnapshot
    local: LocalSnapshot
    provenance: Provenance
```

- [ ] **Step 4: `market/sources/fred.py`**

```python
"""FRED — key'siz CSV endpoint'i. (Resmî API key ister; grafik CSV'si istemez → key yok.)"""

import csv as csv_module
import io

from sonar.market.sources.http import HttpClient

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={ids}"


class FredClient:
    source = "FRED"

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def history(self, series_ids: list[str]) -> list[dict[str, str]]:
        text = self._http.get_text(FRED_CSV.format(ids=",".join(series_ids)))
        return list(csv_module.DictReader(io.StringIO(text)))

    def latest(self, series_ids: list[str]) -> dict[str, float]:
        """Her seri için en son *dolu* değer. FRED eksik günü '.' ile yazar."""
        out: dict[str, float] = {}
        for row in self.history(series_ids):
            for sid in series_ids:
                raw = (row.get(sid) or "").strip()
                if raw and raw != ".":
                    out[sid] = float(raw)
        return out
```

- [ ] **Step 5: `market/sources/global_macro.py`**

```python
"""Global rejim serileri — her market plugin'i bunu KULLANIR (miras almaz)."""

from sonar.domain.macro import GlobalSnapshot
from sonar.market.sources.fred import FredClient

VIX = "VIXCLS"
DXY = "DTWEXBGS"   # Broad Dollar Index
WTI = "DCOILWTICO"


class GlobalMacro:
    def __init__(self, fred: FredClient) -> None:
        self._fred = fred

    def snapshot(self) -> GlobalSnapshot:
        v = self._fred.latest([VIX, DXY, WTI])
        return GlobalSnapshot(vix=v.get(VIX), dxy=v.get(DXY), wti=v.get(WTI))
```

- [ ] **Step 6: `market/us/macro.py`**

```python
"""US'a özel makro. FRED'in aynı istemcisini kullanır; seri seçimi market bilgisidir."""

from sonar.domain.macro import LocalSnapshot
from sonar.market.sources.fred import FredClient

FED_FUNDS = "FEDFUNDS"
CPI = "CPIAUCSL"
Y10 = "DGS10"
Y2 = "DGS2"


class USMacro:
    def __init__(self, fred: FredClient) -> None:
        self._fred = fred

    def snapshot(self) -> LocalSnapshot:
        rows = self._fred.history([FED_FUNDS, CPI, Y10, Y2])
        latest = self._fred.latest([FED_FUNDS, CPI, Y10, Y2])
        y10, y2 = latest.get(Y10), latest.get(Y2)
        return LocalSnapshot(
            fed_funds=latest.get(FED_FUNDS),
            cpi_yoy=self._cpi_yoy(rows),
            yield_10y=y10,
            yield_2y=y2,
            curve_10y_2y=round(y10 - y2, 2) if y10 is not None and y2 is not None else None,
        )

    def _cpi_yoy(self, rows: list[dict[str, str]]) -> float | None:
        """TÜFE endeksi → yıllık % değişim. FRED endeks verir, yüzde değil (bu hesap bizim işimiz)."""
        values = [
            (row["DATE"], float(row[CPI]))
            for row in rows
            if (row.get(CPI) or "").strip() not in ("", ".")
        ]
        if len(values) < 2:
            return None
        latest_date, latest_val = values[-1]
        year_ago = latest_date[:4] and str(int(latest_date[:4]) - 1) + latest_date[4:]
        prior = next((v for d, v in values if d == year_ago), values[0][1])
        if not prior:
            return None
        return round((latest_val - prior) / prior * 100, 2)
```

- [ ] **Step 7: `tools/macro.py` + plugin**

```python
from dataclasses import asdict

from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached


def get_macro_snapshot(
    *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    def compute() -> dict:
        snap = registry.get(market).get_macro_snapshot()
        return {
            "global": asdict(snap.global_),
            "local": asdict(snap.local),
            "source": snap.provenance.source,
        }

    return cached(cache, f"macro:{market}", ttl, compute)
```

`market/us/__init__.py` — kompozisyon (Template Method YOK, spec §4):
```python
    def __init__(self, prices=None, edgar=None, news=None, global_macro=None, local_macro=None):
        http = _default_http()
        fred = FredClient(http)
        self._prices = prices or YFinancePrices()
        self._edgar = edgar or EdgarClient(http)
        self._news = news or USNews(http)
        self._global = global_macro or GlobalMacro(fred)
        self._local = local_macro or USMacro(fred)

    def get_macro_snapshot(self) -> MacroSnapshot:
        return MacroSnapshot(
            global_=self._global.snapshot(),
            local=self._local.snapshot(),
            provenance=Provenance("FRED", time.time()),
        )
```

- [ ] **Step 8: Slow test — gerçek FRED**

`backend/tests/test_macro.py` sonuna:
```python
@pytest.mark.slow
def test_real_fred_returns_vix():
    from sonar.market.us import _default_http

    snap = GlobalMacro(FredClient(_default_http())).snapshot()
    assert snap.vix and 5 < snap.vix < 100  # VIX makul aralıkta
```

- [ ] **Step 9: Run tests**

Run: `cd backend && uv run pytest -q && uv run pytest -m slow -q -k fred`
Expected: 66 passed · slow: 1 passed

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "feat: get_macro_snapshot — FRED (key'siz) + GlobalMacro (VIX/DXY/WTI) + US egri/TUFE"
```

---

### Task A11: DeepAnalysis recipe — deterministik StateGraph

`gather` LLM içermez, tool'ları **paralel** çağırır; bir kaynak düşerse rapor **düşmez** (o bölüm
`unavailable` işaretlenir). `synthesize` **tek** LLM çağrısıdır, token-token akar. Döngü yok → sağlayıcıdan
bağımsız (local Qwen3'te de aynı).

**Files:**
- Create: `backend/sonar/agent/recipes/__init__.py`, `backend/sonar/agent/recipes/deep_analysis.py`
- Test: `backend/tests/test_deep_analysis.py`

**Interfaces:**
- Consumes: A4–A10 tool'ları, `sonar.agent.model.default_model`
- Produces: `gather(ticker, *, registry, cache) -> dict` (bölüm adı → veri | `{"unavailable": str}`) ·
  `make_analyzer(*, registry, cache) -> async (ticker) -> AsyncIterator[tuple[str, dict]]` (Sonar SSE event'leri)

- [ ] **Step 1: Failing test — kısmi hata raporu düşürmez**

`backend/tests/test_deep_analysis.py`:
```python
import pytest
from sonar.agent import events
from sonar.agent.recipes.deep_analysis import gather, make_analyzer
from sonar.market.base import BaseMarketPlugin, Unsupported
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.fundamentals import Fundamentals
from sonar.domain.macro import GlobalSnapshot, LocalSnapshot, MacroSnapshot
from sonar.domain.news import NewsItem
from sonar.domain.quote import Provenance


class PartialMarket(BaseMarketPlugin):
    """Fundamentals patlar (EDGAR 500), gerisi çalışır — rapor ayakta kalmalı."""

    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        candles = [
            Candle(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
            for i in range(250)
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("fake", 1.0))

    def get_fundamentals(self, symbol):
        raise RuntimeError("EDGAR 500")

    def get_news(self, symbol):
        return [NewsItem("Haber", "https://x", "Yahoo Finance", 1)]

    def get_peers(self, symbol):
        raise Unsupported("US: peers")

    def get_macro_snapshot(self):
        return MacroSnapshot(
            GlobalSnapshot(15.1, 122.0, 79.0),
            LocalSnapshot(4.5, 3.0, 4.3, 3.9, 0.4),
            Provenance("FRED", 1.0),
        )


def _ctx(conn):
    reg = MarketRegistry()
    reg.register(PartialMarket())
    return {"registry": reg, "cache": Cache(conn)}


def test_gather_marks_failed_section_unavailable_and_keeps_others(conn):
    out = gather("NVDA", **_ctx(conn))
    assert out["fundamentals"]["unavailable"]          # patladı ama rapor ayakta
    assert out["peers"]["unavailable"] == "US: peers"  # Unsupported da aynı yoldan
    assert out["technicals"]["rsi"] == 100.0
    assert out["macro"]["global"]["vix"] == 15.1
    assert out["news"]["items"][0]["title"] == "Haber"


@pytest.mark.asyncio
async def test_analyzer_streams_steps_chart_then_text(conn):
    class FakeModel:
        async def astream(self, prompt):
            for chunk in ("Makro ", "olumlu."):
                yield type("C", (), {"content": chunk})()

    analyze = make_analyzer(**_ctx(conn), model_factory=lambda: FakeModel())
    seen = [(etype, data) async for etype, data in analyze("NVDA")]
    types = [t for t, _ in seen]

    assert types.count(events.ANALYSIS_STEP) >= 5   # her bölüm bir adım
    assert events.CHART in types
    assert types[-1] == events.TEXT_DELTA
    text = "".join(d["delta"] for t, d in seen if t == events.TEXT_DELTA)
    assert text == "Makro olumlu."
```

> `pytest-asyncio` gerekiyor: `backend/pyproject.toml` → `dev = [..., "pytest-asyncio>=0.24"]`,
> `[tool.pytest.ini_options]` içine `asyncio_mode = "auto"`. Sonra `uv sync`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_deep_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.agent.recipes`

- [ ] **Step 3: `agent/events.py` — taksonomiyi genişlet (yeniden yazma yok)**

Mevcut sabitlerin altına ekle:
```python
ANALYSIS_STEP = "analysis-step"
CHART = "chart"
QUOTE_TICK = "quote-tick"
```
Docstring'deki "M2'de quote-tick · chart **eklenir**" cümlesi artık gerçek — dokunma.

- [ ] **Step 4: `agent/recipes/deep_analysis.py`**

```python
"""DeepAnalysis (UC1) — deterministik reçete (ADR-0007). ReAct YOK, döngü YOK.

gather : LLM içermez; deep tool'ları paralel çağırır. Bir kaynak düşerse rapor düşmez —
         o bölüm {"unavailable": sebep} olur, sentez "bu veri yok" der (sessiz boşluk yasak).
synthesize : TEK LLM çağrısı. Aritmetik yasak — bütün sayılar gather çıktısında hazır (ADR-0003).

LangGraph StateGraph kullanmıyoruz: iki düğüm, dallanma yok, döngü yok → graf makinesi burada
sıfır bilgi saklardı (shallow). asyncio.gather + tek çağrı aynı işi yapıyor. Dallanma gerekirse
(Faz B'de big_players koşullu olsaydı) StateGraph'a yükselt.
"""

import asyncio
from typing import Callable

from loguru import logger

from sonar.agent import events
from sonar.market.base import Unsupported
from sonar.tools.fundamentals import get_fundamentals
from sonar.tools.macro import get_macro_snapshot
from sonar.tools.news import get_news
from sonar.tools.peers import get_peers
from sonar.tools.technicals import get_technicals
from sonar import config

SYNTHESIS_PROMPT = """Sen Sonar'sın; bir ABD borsası araştırma asistanı.

Aşağıda {ticker} için TOPLANMIŞ ve HESAPLANMIŞ veri var. Görevin YALNIZCA sentez:

- Hiçbir aritmetik yapma. Fark, oran, yüzde HESAPLAMA — hepsi zaten aşağıda.
- Veride olmayan bir sayı UYDURMA. Bir bölüm "unavailable" ise "bu veri şu an yok" de, tahmin etme.
- Top-down yaz ve şu sırayı koru:
  1. MAKRO — ortam bu hisseye lehte mi? (faiz, TÜFE, getiri eğrisi, VIX, dolar)
  2. MİKRO — şirketin durumu (gelir, büyüme, marj) + rakiplerle konumu
  3. TEKNİK — trend, momentum, destek/direnç, hacim
  4. HABER — son başlıklar ne söylüyor
  5. SENTEZ — üç katman birbirini destekliyor mu, çelişiyor mu? Ana risk ne?
- Yatırım tavsiyesi verme; gözlem ve risk yaz.
- Türkçe, kısa, net. Her iddianın arkasında yukarıdaki bir sayı olsun.

VERİ:
{data}
"""

# Bölüm adı → o bölümü hesaplayan fonksiyon. TEK kaynak: hem gather hem analyze bunu kullanır
# (ayrı listeler tutulsaydı biri güncellenip diğeri unutulurdu).
def _section_fns(ticker: str, ctx: dict) -> dict[str, Callable[[], dict]]:
    return {
        "macro": lambda: get_macro_snapshot(**ctx, ttl=config.MACRO_TTL_SECONDS),
        "fundamentals": lambda: get_fundamentals(
            ticker, **ctx, ttl=config.FUNDAMENTALS_TTL_SECONDS
        ),
        "technicals": lambda: get_technicals(ticker, **ctx, ttl=config.OHLCV_TTL_SECONDS),
        "news": lambda: get_news(ticker, **ctx, ttl=config.NEWS_TTL_SECONDS),
        "peers": lambda: get_peers(ticker, **ctx, ttl=config.PEERS_TTL_SECONDS),
    }


SECTIONS = ("macro", "fundamentals", "technicals", "news", "peers")


def _run(ticker: str, name: str, fn: Callable[[], dict]) -> dict:
    """Tek bölüm. Kaynak düşerse rapor DÜŞMEZ — bölüm 'unavailable' olur, hata loglanır."""
    try:
        return fn()
    except Unsupported as e:
        logger.info("analiz[{}] {} desteklenmiyor: {}", ticker, name, e)
        return {"unavailable": str(e)}
    except Exception as e:  # noqa: BLE001
        # Why: tek bir dış kaynağın çökmesi (EDGAR 500, RSS timeout) raporun tamamını
        # düşürmemeli. Hata YUTULMUYOR — loglanıyor ve çıktıda görünür kalıyor.
        logger.warning("analiz[{}] {} düştü: {}", ticker, name, e)
        return {"unavailable": f"{type(e).__name__}: {e}"}


def gather(ticker: str, *, registry, cache) -> dict:
    """Deep tool'ları çağırır (senkron, sıralı). LLM yok."""
    fns = _section_fns(ticker, {"registry": registry, "cache": cache})
    return {name: _run(ticker, name, fns[name]) for name in SECTIONS}


def make_analyzer(*, registry, cache, model_factory: Callable | None = None):
    """(ticker) -> Sonar SSE event akışı. Model ilk istekte kurulur (hata SSE error'a düşsün)."""

    async def analyze(ticker: str):
        loop = asyncio.get_running_loop()
        fns = _section_fns(ticker, {"registry": registry, "cache": cache})

        # Bölümler PARALEL koşar; her biri bitince adım event'i akar (sıra korunur).
        tasks = {
            name: loop.run_in_executor(None, _run, ticker, name, fns[name]) for name in SECTIONS
        }
        data: dict[str, dict] = {}
        for name in SECTIONS:
            data[name] = await tasks[name]
            yield events.ANALYSIS_STEP, {
                "section": name,
                "ok": "unavailable" not in data[name],
            }

        yield events.CHART, {"ticker": ticker.upper(), "range": "6mo", "interval": "1d"}

        model = (model_factory or _default_model_factory)()
        prompt = SYNTHESIS_PROMPT.format(
            ticker=ticker.upper(), data=json.dumps(data, ensure_ascii=False, indent=2)
        )
        async for chunk in model.astream(prompt):
            text = getattr(chunk, "content", "")
            if text:
                yield events.TEXT_DELTA, {"delta": text}

    return analyze


def _default_model_factory():
    from sonar.agent.model import default_model

    return default_model()
```

Dosyanın başına `import json` ekle (yukarıdaki import bloğunda).

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_deep_analysis.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: DeepAnalysis recipe — paralel gather (LLM yok) + tek cagrilik synthesize"
```

---

### Task A12: API — `POST /api/analyze` (SSE) + `GET /api/ohlcv`

**Files:**
- Modify: `backend/sonar/api/app.py`
- Test: `backend/tests/test_api_analyze.py`

**Interfaces:**
- Consumes: `make_analyzer` (A11), `get_ohlcv` (A4)
- Produces: `POST /api/analyze {ticker}` → SSE · `GET /api/ohlcv/{ticker}?range=&interval=` → JSON

- [ ] **Step 1: Failing test**

`backend/tests/test_api_analyze.py`:
```python
from fastapi.testclient import TestClient
from sonar.api.app import create_app
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        return OhlcvSeries(
            symbol, interval,
            [Candle(ts=1, open=1.0, high=2.0, low=0.5, close=1.5, volume=10)],
            Provenance("fake", 1.0),
        )


async def _fake_analyzer(ticker: str):
    yield "analysis-step", {"section": "macro", "ok": True}
    yield "chart", {"ticker": ticker, "range": "6mo", "interval": "1d"}
    yield "text-delta", {"delta": "Rapor"}


def _client(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    app = create_app(registry=reg, cache=Cache(conn), analyzer=lambda: _fake_analyzer)
    return TestClient(app)


def test_ohlcv_endpoint_returns_candles(conn):
    r = _client(conn).get("/api/ohlcv/NVDA?range=6mo&interval=1d")
    assert r.status_code == 200
    assert r.json()["candles"][0]["close"] == 1.5


def test_analyze_streams_steps_and_done(conn):
    r = _client(conn).post("/api/analyze", json={"ticker": "NVDA"})
    assert r.status_code == 200
    body = r.text
    assert "event: analysis-step" in body
    assert "event: chart" in body
    assert "event: text-delta" in body
    assert body.rstrip().endswith("event: done\ndata: {}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_api_analyze.py -v`
Expected: FAIL — `TypeError: create_app() got an unexpected keyword argument 'analyzer'`

- [ ] **Step 3: `api/app.py` — iki uç ekle**

`ChatRequest`'in yanına:
```python
class AnalyzeRequest(BaseModel):
    ticker: str
```

`create_app` imzası:
```python
def create_app(
    registry: MarketRegistry | None = None,
    cache: Cache | None = None,
    streamer=None,
    analyzer=None,
) -> FastAPI:
```

`_get_streamer`'ın yanına:
```python
    def _get_analyzer():
        nonlocal analyzer
        if analyzer is None:
            from sonar.agent.recipes.deep_analysis import make_analyzer

            analyzer = lambda: make_analyzer(registry=registry, cache=cache)  # noqa: E731
        return analyzer()
```

`/api/chat`'in altına:
```python
    @app.get("/api/ohlcv/{ticker}")
    def ohlcv(ticker: str, range: str = "6mo", interval: str = "1d") -> dict:
        try:
            return get_ohlcv(
                ticker, range, interval,
                registry=registry, cache=cache, ttl=config.OHLCV_TTL_SECONDS,
            )
        except UnknownSymbol:
            raise HTTPException(status_code=404, detail=f"Sembol bulunamadı: {ticker.upper()}")

    @app.post("/api/analyze")
    async def analyze(req: AnalyzeRequest) -> StreamingResponse:
        async def stream():
            started = time.perf_counter()
            logger.info("analiz[{}] başladı", req.ticker)
            try:
                async for etype, data in _get_analyzer()(req.ticker):
                    if etype == events.ANALYSIS_STEP:
                        logger.info("analiz[{}] {} {}", req.ticker, data["section"],
                                    "✓" if data["ok"] else "✗")
                    yield events.sse(etype, data)
            except Exception as e:  # model/tool hatası → tek error event, sessiz düşme yok
                from sonar.agent.model import explain

                logger.exception("analiz[{}] akış çöktü", req.ticker)
                yield events.sse(events.ERROR, {"message": explain(e)})
            logger.info("analiz[{}] ✓ {:.1f}s", req.ticker, time.perf_counter() - started)
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")
```

`from sonar.tools.ohlcv import get_ohlcv` import'unu dosyanın başına ekle.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 70 passed

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: POST /api/analyze (SSE) + GET /api/ohlcv"
```

---

### Task A13: `GET /api/stream/quotes` — canlı fiyat SSE (polling)

Alpaca WebSocket Task A14'te gelir; bu task **her iki kaynak için de çalışan** polling'i kurar ve
`quote-tick` sözleşmesini sabitler. Frontend hangi yolun kullanıldığını bilmez.

**Files:**
- Create: `backend/sonar/api/quotes.py`
- Modify: `backend/sonar/api/app.py`
- Test: `backend/tests/test_api_quotes_stream.py`

**Interfaces:**
- Produces: `quote_stream(tickers, *, registry, cache, interval, limit) -> AsyncIterator[tuple[str, dict]]` ·
  `GET /api/stream/quotes?tickers=NVDA,AAPL`

- [ ] **Step 1: Failing test**

`backend/tests/test_api_quotes_stream.py`:
```python
import pytest
from sonar.api.quotes import quote_stream
from sonar.domain.money import Money
from sonar.domain.quote import Provenance, Quote
from sonar.market.base import BaseMarketPlugin, UnknownSymbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from decimal import Decimal


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_quote(self, symbol):
        if symbol.ticker == "ZZZZ":
            raise UnknownSymbol("ZZZZ")
        return Quote(
            symbol=symbol,
            price=Money(Decimal("180.42"), "USD"),
            previous_close=Money(Decimal("175.00"), "USD"),
            provenance=Provenance("alpaca", 1.0),
        )


def _ctx(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    return {"registry": reg, "cache": Cache(conn)}


@pytest.mark.asyncio
async def test_quote_stream_emits_tick_per_ticker(conn):
    ticks = [
        data
        async for etype, data in quote_stream(
            ["NVDA", "AAPL"], **_ctx(conn), interval=0, limit=1
        )
    ]
    assert [t["ticker"] for t in ticks] == ["NVDA", "AAPL"]
    assert ticks[0]["price"] == "180.42"
    assert ticks[0]["change_pct"] == 3.1
    assert ticks[0]["source"] == "alpaca"


@pytest.mark.asyncio
async def test_unknown_ticker_does_not_kill_stream(conn):
    ticks = [
        data
        async for _, data in quote_stream(["ZZZZ", "NVDA"], **_ctx(conn), interval=0, limit=1)
    ]
    assert [t["ticker"] for t in ticks] == ["NVDA"]  # bilinmeyen atlanır, akış sürer
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_api_quotes_stream.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.api.quotes`

- [ ] **Step 3: `api/quotes.py`**

```python
"""Canlı fiyat akışı. Çıktı sözleşmesi: quote-tick.

ponytail: polling. Alpaca WebSocket (Task A14) aynı quote-tick'i üretir → frontend farkı bilmez.
Cache TTL'i (60sn) polling aralığından uzun olduğu için cache'i BYPASS ediyoruz; canlı akışın
işi taze veri.
"""

import asyncio

from loguru import logger

from sonar.agent import events
from sonar.domain.symbol import Symbol
from sonar.market.base import UnknownSymbol, Unsupported
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache


async def quote_stream(
    tickers: list[str],
    *,
    registry: MarketRegistry,
    cache: Cache,
    interval: float = 15.0,
    limit: int | None = None,
    market: str = "US",
):
    loop = asyncio.get_running_loop()
    plugin = registry.get(market)
    rounds = 0
    while limit is None or rounds < limit:
        for ticker in tickers:
            symbol = Symbol(ticker, market)
            try:
                quote = await loop.run_in_executor(None, plugin.get_quote, symbol)
            except (UnknownSymbol, Unsupported) as e:
                logger.info("quote-stream: {} atlandı ({})", ticker, e)
                continue
            except Exception as e:  # noqa: BLE001 — tek sembolün hatası akışı düşürmesin
                logger.warning("quote-stream: {} hata ({})", ticker, e)
                continue
            yield events.QUOTE_TICK, {
                "ticker": symbol.ticker,
                "price": str(quote.price.amount),
                "change_pct": round(quote.change_pct, 2),
                "source": quote.provenance.source,
                "ts": quote.provenance.fetched_at,
            }
        rounds += 1
        if limit is None or rounds < limit:
            await asyncio.sleep(interval)
```

- [ ] **Step 4: `api/app.py` — uç**

```python
    @app.get("/api/stream/quotes")
    async def stream_quotes(tickers: str) -> StreamingResponse:
        from sonar.api.quotes import quote_stream

        symbols = [t.strip() for t in tickers.split(",") if t.strip()]

        async def stream():
            try:
                async for etype, data in quote_stream(symbols, registry=registry, cache=cache):
                    yield events.sse(etype, data)
            except asyncio.CancelledError:
                raise  # Why: istemci bağlantıyı kapattı — yutma, propagate et (CLAUDE.md §5)

        return StreamingResponse(stream(), media_type="text/event-stream")
```
Dosyanın başına `import asyncio` ekle.

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 72 passed

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: GET /api/stream/quotes — canli fiyat SSE (polling), quote-tick sozlesmesi"
```

---

### Task A14: Alpaca WebSocket — aynı `quote-tick`, gerçek push

Yalnız Alpaca key'i varsa devreye girer. Aynı event, farklı taşıma → frontend değişmez.

**Files:**
- Create: `backend/sonar/market/us/stream.py`
- Modify: `backend/sonar/api/quotes.py`, `backend/pyproject.toml` (`websockets>=13`)
- Test: `backend/tests/test_alpaca_stream.py`

**Interfaces:**
- Produces: `AlpacaStream(key, secret).ticks(tickers) -> AsyncIterator[dict{ticker, price, ts}]` ·
  `quote_stream(...)` key varsa WS'e, yoksa polling'e düşer

- [ ] **Step 1: Failing test — WS mesajı → tick**

`backend/tests/test_alpaca_stream.py`:
```python
import json

import pytest
from sonar.market.us.stream import AlpacaStream, parse_ws_message


def test_parse_trade_message():
    raw = json.dumps([{"T": "t", "S": "NVDA", "p": 180.42, "t": "2026-07-13T14:00:00Z"}])
    ticks = parse_ws_message(raw)
    assert ticks == [{"ticker": "NVDA", "price": "180.42", "ts": 1784001600.0}]


def test_parse_ignores_control_messages():
    raw = json.dumps([{"T": "success", "msg": "authenticated"}])
    assert parse_ws_message(raw) == []


@pytest.mark.slow
@pytest.mark.skipif_no_alpaca_key
async def test_real_stream_first_tick():
    stream = AlpacaStream(key="...", secret="...")
    async for tick in stream.ticks(["AAPL"]):
        assert float(tick["price"]) > 0
        break
```
> `skipif_no_alpaca_key` yok — bunun yerine `@pytest.mark.skipif(not os.environ.get("SONAR_ALPACA_KEY"), reason="Alpaca key yok")`
> kullan (A3'teki desenin aynısı). Yukarıdaki satırı o hale getir.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_alpaca_stream.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.market.us.stream`

- [ ] **Step 3: Implement**

`backend/sonar/market/us/stream.py`:
```python
"""Alpaca canlı tick akışı (IEX, ücretsiz katman). Çıktı: polling ile AYNI tick sözlüğü."""

import json
from datetime import datetime

WS_URL = "wss://stream.data.alpaca.markets/v2/iex"


def parse_ws_message(raw: str) -> list[dict]:
    """Alpaca mesajı → tick listesi. Kontrol mesajları (auth/subscribe) atlanır."""
    out = []
    for msg in json.loads(raw):
        if msg.get("T") != "t":  # yalnız trade mesajları
            continue
        ts = datetime.fromisoformat(msg["t"].replace("Z", "+00:00")).timestamp()
        out.append({"ticker": msg["S"], "price": str(msg["p"]), "ts": ts})
    return out


class AlpacaStream:
    def __init__(self, key: str, secret: str, url: str = WS_URL) -> None:
        self._key, self._secret, self._url = key, secret, url

    async def ticks(self, tickers: list[str]):
        import websockets

        async with websockets.connect(self._url) as ws:
            await ws.send(json.dumps({"action": "auth", "key": self._key, "secret": self._secret}))
            await ws.send(json.dumps({"action": "subscribe", "trades": tickers}))
            async for raw in ws:
                for tick in parse_ws_message(raw):
                    yield tick
```

- [ ] **Step 4: `api/quotes.py` — key varsa WS'e düş**

`quote_stream`'in başına:
```python
    import os

    key, secret = os.environ.get("SONAR_ALPACA_KEY"), os.environ.get("SONAR_ALPACA_SECRET")
    if key and secret and limit is None:
        # Why: WS gerçek push verir; polling yalnız key yokken (yfinance) ya da testte (limit) kullanılır.
        from sonar.market.us.stream import AlpacaStream

        prev_closes: dict[str, float] = {}
        async for tick in AlpacaStream(key, secret).ticks([t.upper() for t in tickers]):
            ticker = tick["ticker"]
            if ticker not in prev_closes:
                q = await loop.run_in_executor(None, plugin.get_quote, Symbol(ticker, market))
                prev_closes[ticker] = float(q.previous_close.amount)
            prev = prev_closes[ticker]
            change = (float(tick["price"]) - prev) / prev * 100 if prev else 0.0
            yield events.QUOTE_TICK, {**tick, "change_pct": round(change, 2), "source": "alpaca"}
        return
```
(`loop` ve `plugin` tanımlarını bu bloğun **üstüne** taşı.)

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 74 passed

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: Alpaca WebSocket canli tick — polling ile ayni quote-tick sozlesmesi"
```

---

### Task A15: Yeni tool'ları ReAct chat agent'ına aç

Aynı deep tool'lar iki tüketiciye açık (ADR-0007): recipe'ye doğrudan Python çağrısı, chat'e `@tool`.

**Files:**
- Modify: `backend/sonar/agent/tools.py`, `backend/sonar/agent/graph.py`
- Test: `backend/tests/test_agent_tool.py`

**Interfaces:**
- Produces: `make_tools(*, registry, cache) -> list` (7 tool: quote · ohlcv · technicals · fundamentals · news · macro · peers)

- [ ] **Step 1: Failing test**

`backend/tests/test_agent_tool.py` sonuna:
```python
from sonar.agent.tools import make_tools


def test_make_tools_exposes_seven_deep_tools(conn):
    from sonar.market.registry import MarketRegistry
    from sonar.market.us import USMarketPlugin
    from sonar.store.cache import Cache

    reg = MarketRegistry()
    reg.register(USMarketPlugin())
    names = {t.name for t in make_tools(registry=reg, cache=Cache(conn))}
    assert names == {
        "get_stock_quote", "get_price_history", "get_technical_indicators",
        "get_company_fundamentals", "get_stock_news", "get_macro_snapshot", "get_sector_peers",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_agent_tool.py -v`
Expected: FAIL — `ImportError: cannot import name 'make_tools'`

- [ ] **Step 3: `agent/tools.py` — `make_quote_tool`'un yanına**

```python
from sonar import config
from sonar.market.base import Unsupported
from sonar.tools.fundamentals import get_fundamentals
from sonar.tools.macro import get_macro_snapshot
from sonar.tools.news import get_news
from sonar.tools.ohlcv import get_ohlcv
from sonar.tools.peers import get_peers
from sonar.tools.technicals import get_technicals


def make_tools(*, registry: MarketRegistry, cache: Cache) -> list:
    ctx = {"registry": registry, "cache": cache}

    def guard(fn):
        """Tool hataları LLM'e okunur mesaj olarak döner — akış çökmez, sayı uydurulmaz."""
        try:
            return fn()
        except UnknownSymbol as e:
            return {"error": f"Bilinmeyen sembol: {e}"}
        except Unsupported as e:
            return {"error": f"Bu market bunu vermiyor: {e}"}

    @tool
    def get_price_history(ticker: str, range: str = "6mo", interval: str = "1d") -> dict:
        """Hissenin fiyat serisini (mum) döner. range: 1mo|3mo|6mo|1y|2y|5y, interval: 1d|1h|5m."""
        return guard(
            lambda: get_ohlcv(ticker, range, interval, **ctx, ttl=config.OHLCV_TTL_SECONDS)
        )

    @tool
    def get_technical_indicators(ticker: str) -> dict:
        """RSI, MACD, Bollinger, EMA50/200, destek-direnç, OBV, hacim anomalisi — HESAPLANMIŞ döner."""
        return guard(lambda: get_technicals(ticker, **ctx, ttl=config.OHLCV_TTL_SECONDS))

    @tool
    def get_company_fundamentals(ticker: str) -> dict:
        """SEC EDGAR'dan gelir, net kâr, marj, yıllık büyüme (resmî XBRL beyanı)."""
        return guard(
            lambda: get_fundamentals(ticker, **ctx, ttl=config.FUNDAMENTALS_TTL_SECONDS)
        )

    @tool
    def get_stock_news(ticker: str) -> dict:
        """Hisseyle ilgili son haber başlıkları (kaynak + zaman ile)."""
        return guard(lambda: get_news(ticker, **ctx, ttl=config.NEWS_TTL_SECONDS))

    @tool
    def get_macro_snapshot_tool() -> dict:
        """Makro pano: politika faizi, TÜFE, 10Y/2Y getiri, eğri, VIX, dolar endeksi, petrol."""
        return guard(lambda: get_macro_snapshot(**ctx, ttl=config.MACRO_TTL_SECONDS))

    @tool
    def get_sector_peers(ticker: str) -> dict:
        """Aynı sektördeki (SEC SIC kodu) rakip şirketler."""
        return guard(lambda: get_peers(ticker, **ctx, ttl=config.PEERS_TTL_SECONDS))

    get_macro_snapshot_tool.name = "get_macro_snapshot"

    return [
        make_quote_tool(registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS),
        get_price_history,
        get_technical_indicators,
        get_company_fundamentals,
        get_stock_news,
        get_macro_snapshot_tool,
        get_sector_peers,
    ]
```

- [ ] **Step 4: `agent/graph.py` — tek tool yerine hepsi**

`make_streamer` içindeki lazy kurulum bloğunda:
```python
            from sonar.agent.model import default_model
            from sonar.agent.tools import make_tools

            model = default_model()
            logger.info("agent kuruldu — model: {}", getattr(model, "model_name", model))
            agent = build_agent(model=model, tools=make_tools(registry=registry, cache=cache))
```
(`ttl` parametresi artık `make_streamer`'da kullanılmıyor — imzadan **kaldır** ve `api/app.py`'deki
çağrıyı da güncelle: `make_streamer(registry=registry, cache=cache)`.)

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 75 passed

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: 7 deep tool ReAct chat agent'ina acildi (recipe ile ayni tool'lar)"
```

---

### Task A16: Frontend — Lightweight Charts + analiz görünümü + kaynak şeridi

**Files:**
- Create: `frontend/src/chart.tsx`, `frontend/src/analysis.tsx`, `frontend/src/parts.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/chat.tsx`, `frontend/package.json`
- Test: elle doğrulama (aşağıda), frontend test altyapısı yok — M6 CI'de gelir

**Interfaces:**
- Consumes: `POST /api/analyze` (A12), `GET /api/ohlcv` (A12)
- Produces: `<Chart ticker range />` · `<Analysis />` · `Part` tipi genişler: `chart` · `analysis_step`

- [ ] **Step 1: Bağımlılık**

```bash
cd frontend && npm install lightweight-charts@^4.2.0
```

- [ ] **Step 2: `frontend/src/chart.tsx`**

```tsx
import { useEffect, useRef } from "react";
import { createChart, type CandlestickData, type IChartApi } from "lightweight-charts";

type Candle = { ts: number; open: number; high: number; low: number; close: number; volume: number };

export function Chart({ ticker, range = "6mo", interval = "1d" }: {
  ticker: string; range?: string; interval?: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!box.current) return;
    chart.current = createChart(box.current, {
      height: 320,
      layout: { background: { color: "#0d1117" }, textColor: "#e6edf3" },
      grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
      timeScale: { timeVisible: interval !== "1d" },
    });
    const series = chart.current.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350",
      wickUpColor: "#26a69a", wickDownColor: "#ef5350", borderVisible: false,
    });

    let cancelled = false;
    fetch(`/api/ohlcv/${ticker}?range=${range}&interval=${interval}`)
      .then((r) => r.json())
      .then((data: { candles: Candle[] }) => {
        if (cancelled) return;
        const bars: CandlestickData[] = data.candles.map((c) => ({
          time: c.ts as never, open: c.open, high: c.high, low: c.low, close: c.close,
        }));
        series.setData(bars);
        chart.current?.timeScale().fitContent();
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      chart.current?.remove();
    };
  }, [ticker, range, interval]);

  return <div ref={box} style={{ margin: "8px 0", borderRadius: 8, overflow: "hidden" }} />;
}
```

- [ ] **Step 3: `frontend/src/parts.tsx` — registry ortağa çıkar**

`chat.tsx` içindeki `Part` tipi ve `REGISTRY` bu dosyaya taşınır; `chart` ve `analysis_step` eklenir:

```tsx
import type { CSSProperties } from "react";
import { Chart } from "./chart";

export type Part =
  | { kind: "text"; text: string }
  | { kind: "tool_call"; name: string; input: unknown; status: "running" | "done" }
  | { kind: "tool_result"; name: string; output: string }
  | { kind: "chart"; ticker: string; range: string; interval: string }
  | { kind: "analysis_step"; section: string; ok: boolean }
  | { kind: "error"; message: string };

const card: CSSProperties = {
  margin: "6px 0", padding: "6px 10px", borderRadius: 8,
  background: "#0d1117", border: "1px solid #21262d", fontSize: 13,
};
const codeStyle: CSSProperties = {
  display: "block", marginTop: 4, color: "#7ee787", fontSize: 12, wordBreak: "break-all",
};

const SECTION_LABEL: Record<string, string> = {
  macro: "Makro", fundamentals: "Temel", technicals: "Teknik",
  news: "Haber", peers: "Rakipler", big_players: "Büyük oyuncular",
};

export const REGISTRY: Record<Part["kind"], (p: Part) => JSX.Element> = {
  text: (p) => <span style={{ whiteSpace: "pre-wrap" }}>{(p as any).text}</span>,
  tool_call: (p) => {
    const t = p as Extract<Part, { kind: "tool_call" }>;
    return (
      <div style={card}>
        <span style={{ opacity: 0.7 }}>{t.status === "running" ? "⏳" : "✓"} tool</span>{" "}
        <b>{t.name}</b>
        <code style={codeStyle}>{JSON.stringify(t.input)}</code>
      </div>
    );
  },
  tool_result: (p) => {
    const t = p as Extract<Part, { kind: "tool_result" }>;
    return (
      <div style={card}>
        <span style={{ opacity: 0.7 }}>↳ {t.name}</span>
        <code style={codeStyle}>{t.output}</code>
      </div>
    );
  },
  chart: (p) => {
    const c = p as Extract<Part, { kind: "chart" }>;
    return <Chart ticker={c.ticker} range={c.range} interval={c.interval} />;
  },
  analysis_step: (p) => {
    const s = p as Extract<Part, { kind: "analysis_step" }>;
    return (
      <div style={{ ...card, opacity: s.ok ? 0.85 : 0.6 }}>
        {s.ok ? "✓" : "⚠"} {SECTION_LABEL[s.section] ?? s.section}
        {!s.ok && <span style={{ color: "#f0883e" }}> — veri yok</span>}
      </div>
    );
  },
  error: (p) => <span style={{ color: "#f87171" }}>{(p as any).message}</span>,
};

export function MessagePart({ part }: { part: Part }) {
  return REGISTRY[part.kind](part);
}
```

`chat.tsx`'ten `Part`/`REGISTRY`/`MessagePart`/`card`/`codeStyle` tanımlarını **sil**, yerine
`import { MessagePart, type Part } from "./parts";` koy.

- [ ] **Step 4: `frontend/src/analysis.tsx`**

```tsx
import { useState } from "react";
import { MessagePart, type Part } from "./parts";
import { streamSSE } from "./chat";

export function Analysis() {
  const [ticker, setTicker] = useState("");
  const [parts, setParts] = useState<Part[]>([]);
  const [busy, setBusy] = useState(false);

  async function run() {
    const t = ticker.trim().toUpperCase();
    if (!t || busy) return;
    setParts([]);
    setBusy(true);
    try {
      await streamSSE("/api/analyze", { ticker: t }, (type, data) => {
        setParts((prev) => {
          if (type === "text-delta") {
            const last = prev[prev.length - 1];
            if (last?.kind === "text") {
              return [...prev.slice(0, -1), { kind: "text", text: last.text + data.delta }];
            }
            return [...prev, { kind: "text", text: data.delta }];
          }
          if (type === "analysis-step")
            return [...prev, { kind: "analysis_step", section: data.section, ok: data.ok }];
          if (type === "chart")
            return [...prev, { kind: "chart", ticker: data.ticker, range: data.range, interval: data.interval }];
          if (type === "error") return [...prev, { kind: "error", message: data.message }];
          return prev;
        });
      });
    } catch (e) {
      setParts((p) => [...p, { kind: "error", message: String(e) }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Sembol — ör. NVDA"
          style={{ flex: 1, padding: "10px 12px", borderRadius: 8, border: "1px solid #30363d", background: "#0d1117", color: "#e6edf3" }}
        />
        <button
          onClick={run}
          disabled={busy}
          style={{ padding: "10px 18px", borderRadius: 8, border: 0, background: "#1f6feb", color: "#fff", cursor: "pointer" }}
        >
          {busy ? "Analiz ediliyor…" : "Derin analiz"}
        </button>
      </div>
      <div style={{ marginTop: 16 }}>
        {parts.map((p, i) => (
          <MessagePart key={i} part={p} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: `chat.tsx` — SSE okuyucusunu dışa aç ve tekrarı kaldır**

`streamChat` fonksiyonunu genelleştir ve **export** et:
```tsx
export async function streamSSE(
  url: string,
  body: unknown,
  onEvent: (type: string, data: any) => void,
) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok || !resp.body) throw new Error(`istek hatası: ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i);
      buf = buf.slice(i + 2);
      let type = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) type = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onEvent(type, JSON.parse(data));
    }
  }
}
```
`Chat` içindeki `streamChat(msg, cb)` çağrısını `streamSSE("/api/chat", { message: msg }, cb)` yap;
eski `streamChat` tanımını **sil**.

- [ ] **Step 6: `App.tsx` — iki sekme + kaynak şeridi**

```tsx
import { useEffect, useState } from "react";
import { Analysis } from "./analysis";
import { Chat } from "./chat";

function SourceBanner() {
  const [source, setSource] = useState<string | null>(null);
  useEffect(() => {
    fetch("/api/quote/AAPL")
      .then((r) => r.json())
      .then((q) => setSource(q.source))
      .catch(() => {});
  }, []);
  if (source !== "yfinance") return null;
  return (
    <div style={{ padding: "8px 20px", background: "#3d2b00", color: "#f0d68a", fontSize: 13 }}>
      Fiyat verisi Yahoo'dan kazınıyor (resmî değil, kırılgan). Ücretsiz{" "}
      <a href="https://alpaca.markets" target="_blank" rel="noreferrer" style={{ color: "#f0d68a" }}>
        Alpaca
      </a>{" "}
      key'i ile resmî veriye geç — <code>SONAR_ALPACA_KEY</code>.
    </div>
  );
}

export function App() {
  const [tab, setTab] = useState<"analysis" | "chat">("analysis");
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0d1117", color: "#e6edf3" }}>
      <header style={{ display: "flex", gap: 16, alignItems: "center", padding: "12px 20px", borderBottom: "1px solid #21262d" }}>
        <b>Sonar</b>
        {(["analysis", "chat"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: "none", border: 0, cursor: "pointer", padding: "4px 8px",
              color: tab === t ? "#e6edf3" : "#7d8590",
              borderBottom: tab === t ? "2px solid #1f6feb" : "2px solid transparent",
            }}
          >
            {t === "analysis" ? "Derin Analiz" : "Sohbet"}
          </button>
        ))}
      </header>
      <SourceBanner />
      <div style={{ flex: 1, overflowY: "auto" }}>{tab === "analysis" ? <Analysis /> : <Chat />}</div>
    </div>
  );
}
```
`Chat` bileşeninin en dış `div`'indeki `height: "100vh"` ve `background` stillerini **kaldır**
(artık `App` sarmalıyor); `header`'ını da sil.

- [ ] **Step 7: Build ve elle doğrula**

```bash
cd frontend && npm run build
```
Expected: hata yok, `dist/` üretildi.

Elle:
```bash
cd backend && uv run sonar     # llama-server ayakta olmalı
```
Tarayıcı → "Derin Analiz" → `NVDA` → Enter. Görülmesi gereken:
1. Sırayla `✓ Makro`, `✓ Temel`, `✓ Teknik`, `✓ Haber`, `✓ Rakipler` adımları
2. Mum grafiği çizilir
3. Rapor token-token akar; Makro→Mikro→Teknik→Haber→Sentez sırasıyla

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: Lightweight Charts + derin analiz gorunumu + part registry (chart/analysis_step) + kaynak seridi"
```

---

## 🚦 MERGE KAPISI — Faz A DoD

Faz B'ye geçmeden **hepsi yeşil olmalı**:

- [ ] `cd backend && uv run pytest -q` → **75+ passed**, 0 failed
- [ ] `cd backend && uv run pytest -m slow -q` → gerçek EDGAR/FRED/(Alpaca) çağrıları geçiyor
- [ ] `uv run sonar` → tarayıcıda `NVDA` → **top-down rapor + Lightweight Chart** (spec DoD)
- [ ] Rapordaki her sayı bir tool çıktısında **birebir** bulunabiliyor (LLM aritmetik yapmadı)
- [ ] Alpaca key'i **olmadan** da çalışıyor; kaynak şeridi görünüyor
- [ ] Bir kaynağı kasten bozunca (ör. EDGAR URL'ini boz) rapor **düşmüyor** — bölüm "veri yok" diyor
- [ ] `test_layering.py` yeşil (analytics/market/sources provider ithal etmiyor)
- [ ] `git log --oneline` → yapısal (refactor) ve davranışsal (feat) commit'ler ayrı

Kapı geçilince: `docs/ROADMAP.md`'de M2 satırına "Faz A ✅" notu düş, commit'le.

---

# FAZ B — Big Players

### Task B0: SPIKE — ölç, sonra kur (kod yazılmaz)

13F'in üç bilinmeyeni var ve **hiçbiri tahminle geçilemez**. Bu task kod üretmez, **rapor** üretir.

**Files:**
- Create: `docs/superpowers/plans/2026-07-13-13f-spike-raporu.md`
- Scratch: `C:\Users\Ferha\AppData\Local\Temp\claude\...\scratchpad\` (indirilen dosyalar buraya, repoya değil)

- [ ] **Step 1: Bir çeyreklik 13F veri setini indir ve ölç**

```bash
# DERA 13F yapılandırılmış veri seti (çeyreklik)
curl -A "Sonar/0.1 (ferhat.ersoy@egeist.com.tr)" -o 13f.zip \
  https://www.sec.gov/files/dera/data/form-13f-data-sets/2026q1_form13f.zip
unzip -o 13f.zip -d 13f/
ls -la 13f/
wc -l 13f/INFOTABLE.tsv 13f/SUBMISSION.tsv 13f/COVERPAGE.tsv
du -sh 13f/
```
**Kaydet:** ZIP boyutu · INFOTABLE satır sayısı · açılmış toplam MB.

> URL 404 verirse: https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets
> sayfasından **en güncel çeyreğin** gerçek linkini al ve rapora yaz.

- [ ] **Step 2: SQLite'a yükle, süre ve boyut ölç — filtreli VE filtresiz**

Scratchpad'de tek seferlik script (repoya girmez):
```python
import csv, sqlite3, time, sys

conn = sqlite3.connect("13f_test.db")
conn.execute("""CREATE TABLE holdings(
  cusip TEXT, cik TEXT, shares INTEGER, value INTEGER, put_call TEXT, accession TEXT)""")

started = time.perf_counter()
rows = 0
with open("13f/INFOTABLE.tsv", encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        conn.execute(
            "INSERT INTO holdings VALUES (?,?,?,?,?,?)",
            (row["CUSIP"], row.get("ACCESSION_NUMBER"), int(float(row["SSHPRNAMT"] or 0)),
             int(float(row["VALUE"] or 0)), row.get("PUTCALL") or "", row["ACCESSION_NUMBER"]),
        )
        rows += 1
conn.commit()
print(f"{rows} satır, {time.perf_counter()-started:.1f}s")
```
```bash
python load.py && ls -la 13f_test.db
```
**Kaydet:** satır sayısı · yükleme süresi · **DB boyutu (MB)**.

- [ ] **Step 3: CUSIP→ticker eşleşme oranını ölç (İKİ yol birlikte)**

```bash
# (i) SEC fails-to-deliver — CUSIP + SYMBOL birlikte
curl -A "Sonar/0.1 (ferhat.ersoy@egeist.com.tr)" -o ftd.zip \
  https://www.sec.gov/files/data/fails-deliver-data/cnsfails202606a.zip
unzip -o ftd.zip

# (ii) SEC company_tickers.json — isim ↔ ticker
curl -A "Sonar/0.1 (ferhat.ersoy@egeist.com.tr)" -o tickers.json \
  https://www.sec.gov/files/company_tickers.json
```

Ölçüm scripti:
```python
# INFOTABLE'daki DISTINCT CUSIP kümesinin kaçı ticker'a çevrilebiliyor?
# (i) FTD haritası ile, (ii) + issuer adı fuzzy eşleşmesi ile → İKİ ORAN raporla.
```
**Kaydet:** distinct CUSIP sayısı · FTD ile eşleşen % · FTD+isim ile eşleşen % · **NVDA'nın CUSIP'i
bulunuyor mu** (67066G104).

- [ ] **Step 4: Δ'yı elle doğrula**

İki çeyreği (2025q4 + 2026q1) yükle, NVDA'nın CUSIP'i için bir filer seç ve Δ'yı hesapla.
**Aynı sayıyı** EDGAR'ın kendi arayüzünde (o filer'ın 13F-HR belgesinde) veya WhaleWisdom/Dataroma'da
**gözle doğrula**. Eşleşmiyorsa neden? (amendment mi, birim mi, hisse-bölünmesi mi?)

- [ ] **Step 5: Amendment tiplerini say**

```bash
cut -f<AMENDMENT_TYPE sütunu> 13f/COVERPAGE.tsv | sort | uniq -c
```
**Kaydet:** `RESTATEMENT` ve `NEW HOLDINGS` kaç tane? (Sıfırsa bile kural yazılacak — bir sonraki
çeyrek gelir.)

- [ ] **Step 6: SEC 13f-2 / Form SHO toplulaştırılmış short verisi yayında mı?**

https://www.sec.gov/data-research adresinde ara. Yayındaysa: format, sıklık, gecikme.
**Kaydet:** var/yok + varsa URL.

- [ ] **Step 7: FINRA short interest endpoint'i key'siz mi?**

```bash
curl -sI "https://cdn.finra.org/equity/otcmarket/biweekly/" | head -3
```
FINRA'nın ücretsiz-key'siz dosya yolu bulunamazsa **yedek plan**: yfinance `.info` →
`sharesShort`, `shortRatio` (ikinci-el; Provenance "Yahoo (ikinci-el)" der).
**Kaydet:** hangi yol çalışıyor.

- [ ] **Step 8: Raporu yaz ve KARAR AL**

`docs/superpowers/plans/2026-07-13-13f-spike-raporu.md`:
```markdown
# 13F Spike Raporu (2026-07-…)

## Ölçümler
| Metrik | Değer |
|---|---|
| ZIP boyutu | … MB |
| INFOTABLE satır | … |
| SQLite (filtresiz) | … MB · … sn |
| SQLite (ticker'a eşleşenler) | … MB · … sn |
| Distinct CUSIP | … |
| CUSIP→ticker (FTD) | %… |
| CUSIP→ticker (FTD + isim) | %… |
| Δ elle doğrulama | ✅/❌ (filer: …, beklenen: …, hesaplanan: …) |
| Amendment tipleri | RESTATEMENT: … · NEW HOLDINGS: … |
| SEC 13f-2 short | var/yok |
| FINRA short interest | key'siz ✅ / yedek: yfinance |

## Kararlar
1. **Yol:** toplu indeks ✅ / küratörlü filer evreni ❌ (eşik: eşleşme ≥%90)
2. **Filtreleme:** eşleşmeyen CUSIP satırları atılsın mı? → … (AÇIK KARAR, spec §7)
3. **Sürpriz/uyarı:** …
```

- [ ] **Step 9: Commit + KULLANICI ONAYI**

```bash
git add docs/superpowers/plans/2026-07-13-13f-spike-raporu.md
git commit -m "spike: 13F veri seti olculdu — yol karari + acik karar (filtreleme) icin veri"
```

> **DUR.** Raporu kullanıcıya göster. **Yol kararı** (toplu indeks vs küratörlü) ve **filtreleme kararı**
> onaylanmadan B1'e geçme. Eşleşme %90'ın altındaysa B1'in içeriği tamamen değişir.

---

### Task B1: 13F ingestion — DERA veri seti → SQLite

> **Ön koşul:** B0 raporu onaylandı, yol = **toplu indeks**. Küratörlü yola düşüldüyse bu task'ın
> Step 3'ü değişir (ZIP yerine ~50 CIK'in filing'leri tek tek çekilir); şema ve geri kalanı aynıdır.

**Files:**
- Create: `backend/sonar/store/holdings_repo.py`, `backend/sonar/market/us/thirteen_f.py`
- Modify: `backend/sonar/store/db.py`
- Test: `backend/tests/test_holdings_repo.py`

**Interfaces:**
- Produces: `HoldingsRepo(conn)` · `.ingest(rows, quarter)` · `.holders_of(cusip, quarter) -> list[HolderPosition]` ·
  `.filer_holdings(cik, quarter)` · `.quarters() -> list[str]` · `.prune(keep=2)` ·
  `parse_13f_zip(data: bytes) -> Iterator[Row]` · `CusipMap.ticker_for(cusip) -> str | None`

- [ ] **Step 1: Failing test — amendment kuralı ve prune**

`backend/tests/test_holdings_repo.py`:
```python
from sonar.store.holdings_repo import HoldingsRepo, Row


def _rows(cik: str, cusip: str, shares: int, accession: str, amendment: str = "") -> list[Row]:
    return [Row(
        accession=accession, cik=cik, filer_name="ACME CAP", cusip=cusip,
        issuer_name="NVIDIA CORP", shares=shares, value=shares * 10,
        put_call="", amendment_type=amendment,
    )]


def test_restatement_replaces_previous_filing(conn):
    repo = HoldingsRepo(conn)
    repo.ingest(_rows("0001", "67066G104", 1000, "a-1"), quarter="2026Q1")
    repo.ingest(_rows("0001", "67066G104", 400, "a-2", "RESTATEMENT"), quarter="2026Q1")
    holders = repo.holders_of("67066G104", "2026Q1")
    assert len(holders) == 1
    assert holders[0].shares == 400  # düzeltme eskisini SİLDİ


def test_new_holdings_amendment_appends(conn):
    repo = HoldingsRepo(conn)
    repo.ingest(_rows("0001", "67066G104", 1000, "a-1"), quarter="2026Q1")
    repo.ingest(_rows("0001", "88160R101", 50, "a-2", "NEW HOLDINGS"), quarter="2026Q1")
    assert len(repo.filer_holdings("0001", "2026Q1")) == 2  # ekleme — eskisi durur


def test_prune_keeps_last_n_quarters(conn):
    repo = HoldingsRepo(conn)
    for q in ("2025Q3", "2025Q4", "2026Q1"):
        repo.ingest(_rows("0001", "67066G104", 100, f"a-{q}"), quarter=q)
    repo.prune(keep=2)
    assert repo.quarters() == ["2025Q4", "2026Q1"]
    assert repo.holders_of("67066G104", "2025Q3") == []


def test_holders_of_returns_filer_name_and_put_call(conn):
    repo = HoldingsRepo(conn)
    rows = _rows("0001", "67066G104", 1000, "a-1")
    rows.append(Row(
        accession="a-1", cik="0001", filer_name="ACME CAP", cusip="67066G104",
        issuer_name="NVIDIA CORP", shares=200, value=2000, put_call="Put", amendment_type="",
    ))
    repo.ingest(rows, quarter="2026Q1")
    holders = repo.holders_of("67066G104", "2026Q1")
    assert {h.put_call for h in holders} == {"", "Put"}  # opsiyon pozisyonu görünür (spec §7)
    assert holders[0].filer_name == "ACME CAP"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_holdings_repo.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.store.holdings_repo`

- [ ] **Step 3: `store/db.py` — şema**

`_SCHEMA`'ya ekle:
```sql
CREATE TABLE IF NOT EXISTS holdings (
  quarter     TEXT NOT NULL,
  accession   TEXT NOT NULL,
  cik         TEXT NOT NULL,
  filer_name  TEXT NOT NULL,
  cusip       TEXT NOT NULL,
  issuer_name TEXT NOT NULL,
  shares      INTEGER NOT NULL,
  value       INTEGER NOT NULL,
  put_call    TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_holdings_cusip   ON holdings(cusip, quarter);
CREATE INDEX IF NOT EXISTS idx_holdings_cik     ON holdings(cik, quarter);

-- Ham veri 2 çeyrek tutulur; trend için sembol başına TEK özet satırı sonsuza kalır (spec §7).
CREATE TABLE IF NOT EXISTS symbol_quarterly (
  cusip        TEXT NOT NULL,
  quarter      TEXT NOT NULL,
  total_shares INTEGER NOT NULL,
  filer_count  INTEGER NOT NULL,
  PRIMARY KEY (cusip, quarter)
);

CREATE TABLE IF NOT EXISTS cusip_ticker (
  cusip  TEXT PRIMARY KEY,
  ticker TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cusip_ticker_ticker ON cusip_ticker(ticker);
```

- [ ] **Step 4: `store/holdings_repo.py`**

```python
"""13F pozisyon deposu. Ham veri son N çeyrek; trend için özet satırı kalıcı (spec §7).

Amendment kuralı (naif 'en son kazanır' YANLIŞ olurdu):
  RESTATEMENT   → filer'ın o çeyrekteki TÜM satırlarını sil, yenilerini koy
  NEW HOLDINGS  → ekle (eskisi durur)
Ayrılmazsa Δ saçmalar: pozisyon ya kaybolur ya iki katına çıkar.
"""

import sqlite3
import threading
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Row:
    accession: str
    cik: str
    filer_name: str
    cusip: str
    issuer_name: str
    shares: int
    value: int
    put_call: str
    amendment_type: str


@dataclass(frozen=True, slots=True)
class HolderPosition:
    cik: str
    filer_name: str
    shares: int
    value: int
    put_call: str


class HoldingsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.Lock()  # ponytail: tek kullanıcı — Cache ile aynı desen

    def ingest(self, rows: list[Row], quarter: str) -> None:
        if not rows:
            return
        with self._lock:
            restating = {r.cik for r in rows if r.amendment_type.upper() == "RESTATEMENT"}
            for cik in restating:
                self._conn.execute(
                    "DELETE FROM holdings WHERE quarter = ? AND cik = ?", (quarter, cik)
                )
            self._conn.executemany(
                """INSERT INTO holdings
                   (quarter, accession, cik, filer_name, cusip, issuer_name, shares, value, put_call)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    (quarter, r.accession, r.cik, r.filer_name, r.cusip, r.issuer_name,
                     r.shares, r.value, r.put_call)
                    for r in rows
                ],
            )
            self._conn.execute(
                """INSERT OR REPLACE INTO symbol_quarterly (cusip, quarter, total_shares, filer_count)
                   SELECT cusip, ?, SUM(shares), COUNT(DISTINCT cik)
                   FROM holdings WHERE quarter = ? AND put_call = '' GROUP BY cusip""",
                (quarter, quarter),
            )
            self._conn.commit()

    def holders_of(self, cusip: str, quarter: str) -> list[HolderPosition]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT cik, filer_name, shares, value, put_call FROM holdings
                   WHERE cusip = ? AND quarter = ? ORDER BY value DESC""",
                (cusip, quarter),
            ).fetchall()
        return [HolderPosition(*r) for r in rows]

    def filer_holdings(self, cik: str, quarter: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT cusip, issuer_name, shares, value, put_call FROM holdings
                   WHERE cik = ? AND quarter = ? ORDER BY value DESC""",
                (cik, quarter),
            ).fetchall()
        return [
            {"cusip": c, "issuer": i, "shares": s, "value": v, "put_call": p}
            for c, i, s, v, p in rows
        ]

    def quarters(self) -> list[str]:
        with self._lock:
            return [
                r[0]
                for r in self._conn.execute(
                    "SELECT DISTINCT quarter FROM holdings ORDER BY quarter"
                )
            ]

    def trend(self, cusip: str) -> list[dict]:
        """Sahiplik trendi — ham veri silinse de yaşar (özet tablosu)."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT quarter, total_shares, filer_count FROM symbol_quarterly
                   WHERE cusip = ? ORDER BY quarter""",
                (cusip,),
            ).fetchall()
        return [{"quarter": q, "total_shares": t, "filer_count": f} for q, t, f in rows]

    def prune(self, keep: int = 2) -> None:
        """Eski çeyreklerin HAM satırlarını sil. symbol_quarterly'ye DOKUNMA (trend orada yaşıyor)."""
        keepers = self.quarters()[-keep:]
        if not keepers:
            return
        with self._lock:
            placeholders = ",".join("?" * len(keepers))
            self._conn.execute(
                f"DELETE FROM holdings WHERE quarter NOT IN ({placeholders})", keepers
            )
            self._conn.commit()
```

- [ ] **Step 5: `market/us/thirteen_f.py` — ZIP parse + CUSIP haritası**

```python
"""DERA 13F veri seti → Row akışı. Kaynak formatı burada biter; store domain görür."""

import csv
import io
import zipfile
from collections.abc import Iterator

from sonar.store.holdings_repo import Row

DERA_ZIP = "https://www.sec.gov/files/dera/data/form-13f-data-sets/{quarter}_form13f.zip"


def parse_13f_zip(data: bytes) -> Iterator[Row]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        cover = _table(z, "COVERPAGE.tsv")
        subs = _table(z, "SUBMISSION.tsv")
        amendments = {r["ACCESSION_NUMBER"]: (r.get("AMENDMENTTYPE") or "") for r in cover}
        filers = {r["ACCESSION_NUMBER"]: (r.get("FILINGMANAGER_NAME") or "?") for r in subs}
        ciks = {r["ACCESSION_NUMBER"]: (r.get("CIK") or "") for r in subs}

        for r in _table(z, "INFOTABLE.tsv"):
            acc = r["ACCESSION_NUMBER"]
            yield Row(
                accession=acc,
                cik=ciks.get(acc, ""),
                filer_name=filers.get(acc, "?"),
                cusip=(r.get("CUSIP") or "").strip().upper(),
                issuer_name=(r.get("NAMEOFISSUER") or "").strip(),
                shares=int(float(r.get("SSHPRNAMT") or 0)),
                value=int(float(r.get("VALUE") or 0)),
                put_call=(r.get("PUTCALL") or "").strip(),
                amendment_type=amendments.get(acc, ""),
            )


def _table(z: zipfile.ZipFile, name: str) -> list[dict]:
    with z.open(name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
        return list(csv.DictReader(text, delimiter="\t"))
```

> **B0 raporuna göre sütun adlarını doğrula.** DERA şeması çeyrekler arası ufak değişebilir; spike'ta
> gördüğün gerçek başlıkları kullan (yukarıdakiler tahmin değil, ölçümden gelmeli).

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest tests/test_holdings_repo.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: 13F deposu — amendment kurali (RESTATEMENT/NEW HOLDINGS) + ozet satiri + prune"
```

---

### Task B2: Arka planda ingestion + `GET /api/ingest/status`

Uygulama açılışında (spec §7: **2-b**) arka planda indirir; **sessiz değil** — durum uçtan görünür.
Faz A bundan **bağımsız** çalışır.

**Files:**
- Create: `backend/sonar/store/ingest.py`
- Modify: `backend/sonar/api/app.py`
- Test: `backend/tests/test_ingest.py`

**Interfaces:**
- Produces: `IngestState` (`idle|running|ready|error`, `progress`, `quarter`, `message`) ·
  `Ingester(repo, fetch).run_async()` · `GET /api/ingest/status`

- [ ] **Step 1: Failing test**

`backend/tests/test_ingest.py`:
```python
import pytest
from sonar.store.holdings_repo import HoldingsRepo, Row
from sonar.store.ingest import Ingester


def _rows():
    return [Row("a-1", "0001", "ACME", "67066G104", "NVIDIA CORP", 100, 1000, "", "")]


@pytest.mark.asyncio
async def test_ingest_marks_ready_and_writes_rows(conn):
    repo = HoldingsRepo(conn)
    ing = Ingester(repo, fetch=lambda quarter: _rows(), quarters=["2026Q1"])
    assert ing.state.status == "idle"
    await ing.run()
    assert ing.state.status == "ready"
    assert ing.state.progress == 1.0
    assert repo.holders_of("67066G104", "2026Q1")[0].shares == 100


@pytest.mark.asyncio
async def test_ingest_error_is_visible_not_silent(conn):
    def boom(quarter):
        raise RuntimeError("SEC 503")

    ing = Ingester(HoldingsRepo(conn), fetch=boom, quarters=["2026Q1"])
    await ing.run()
    assert ing.state.status == "error"
    assert "SEC 503" in ing.state.message  # sessiz düşme yok
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.store.ingest`

- [ ] **Step 3: `store/ingest.py`**

```python
"""13F ingestion — uygulama açılışında arka planda. Durum GÖRÜNÜR (spec §7: sessiz indirme yok)."""

import asyncio
from dataclasses import dataclass, field
from typing import Callable

from loguru import logger

from sonar.store.holdings_repo import HoldingsRepo, Row


@dataclass
class IngestState:
    status: str = "idle"  # idle | running | ready | error
    progress: float = 0.0
    quarter: str = ""
    message: str = ""


def _default_quarters(n: int = 2) -> list[str]:
    """Son n çeyrek. 13F 45 gün gecikmeli → bu çeyreğin verisi henüz yok, bir önceki tam çeyrekten geriye."""
    from datetime import date

    today = date.today()
    q = (today.month - 1) // 3  # bulunduğumuz çeyrek (0-3); tamamlanmış son çeyrek bunun bir öncesi
    year = today.year
    out = []
    for _ in range(n):
        q -= 1
        if q < 0:
            q, year = 3, year - 1
        out.append(f"{year}Q{q + 1}")
    return sorted(out)


class Ingester:
    def __init__(
        self,
        repo: HoldingsRepo,
        fetch: Callable[[str], list[Row]],
        quarters: list[str] | None = None,
    ) -> None:
        self._repo = repo
        self._fetch = fetch
        self._quarters = quarters or _default_quarters()
        self.state = IngestState()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        self.state = IngestState(status="running")
        try:
            for i, quarter in enumerate(self._quarters):
                if quarter in self._repo.quarters():
                    logger.info("13F {} zaten var — atlanıyor", quarter)
                else:
                    self.state.quarter = quarter
                    logger.info("13F {} indiriliyor…", quarter)
                    rows = await loop.run_in_executor(None, self._fetch, quarter)
                    await loop.run_in_executor(None, self._repo.ingest, rows, quarter)
                    logger.info("13F {} yüklendi: {} satır", quarter, len(rows))
                self.state.progress = (i + 1) / len(self._quarters)
            await loop.run_in_executor(None, self._repo.prune, 2)
            self.state.status = "ready"
        except Exception as e:  # noqa: BLE001
            # Why: ingestion çökerse uygulama ayakta kalmalı (Faz A çalışıyor), ama hata GÖRÜNMELİ.
            logger.exception("13F ingestion çöktü")
            self.state.status = "error"
            self.state.message = f"{type(e).__name__}: {e}"
```

- [ ] **Step 4: `api/app.py` — startup task + status ucu**

```python
    ingester = None

    @app.on_event("startup")
    async def _start_ingest() -> None:
        nonlocal ingester
        import os

        if os.environ.get("SONAR_SKIP_INGEST"):  # testler ve CI için
            return
        from sonar.market.sources.http import HttpClient
        from sonar.market.us.thirteen_f import DERA_ZIP, parse_13f_zip
        from sonar.store.holdings_repo import HoldingsRepo
        from sonar.store.ingest import Ingester

        http = HttpClient(f"Sonar/0.1 ({os.environ.get('SONAR_CONTACT', 'sonar@localhost')})")

        def fetch(quarter: str):
            data = http.get_bytes(DERA_ZIP.format(quarter=quarter.lower()))
            return list(parse_13f_zip(data))

        ingester = Ingester(HoldingsRepo(cache._conn), fetch)
        asyncio.create_task(ingester.run())  # ponytail: fire-and-forget; hata state'te görünür

    @app.get("/api/ingest/status")
    def ingest_status() -> dict:
        if ingester is None:
            return {"status": "idle", "progress": 0.0, "quarter": "", "message": ""}
        s = ingester.state
        return {
            "status": s.status, "progress": s.progress,
            "quarter": s.quarter, "message": s.message,
        }
```

> **Uyarı:** `cache._conn`'a erişmek private'a el atmaktır. **Düzelt:** `create_app` zaten `conn`'u
> `Cache(connect(...))` içinde üretiyor — `conn`'u yerel değişkende tut ve hem `Cache`'e hem
> `HoldingsRepo`'ya ver. (`create_app` başında: `conn = connect(config.DB_PATH)`; `cache = cache or Cache(conn)`.)
> Test enjeksiyonu için `create_app(..., conn=None)` parametresi ekle.
>
> **asyncio.create_task referansı:** görev nesnesini bir set'te tut (`_tasks.add(task)`), yoksa GC
> görevi ortadan kaldırabilir (Python gotcha).

- [ ] **Step 5: `pyproject.toml` — testlerde ingestion kapalı**

`[tool.pytest.ini_options]` içine:
```toml
env = ["SONAR_SKIP_INGEST=1"]
```
(`pytest-env` gerekiyorsa `dev` grubuna ekle; alternatif: `conftest.py`'de
`os.environ.setdefault("SONAR_SKIP_INGEST", "1")` — **bunu tercih et**, yeni bağımlılık yok.)

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 81 passed

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: 13F arka plan ingestion + GET /api/ingest/status (sessiz indirme yok)"
```

---

### Task B3: `analytics/holdings.py` — Δ sınıflaması + sahiplik trendi

Saf matematik. Plugin'de değil çekirdekte — her market için aynı.

**Files:**
- Create: `backend/sonar/analytics/holdings.py`
- Test: `backend/tests/test_analytics_holdings.py`

**Interfaces:**
- Produces: `classify_delta(prev_shares, cur_shares) -> str` (`new|exit|add|trim|hold`) ·
  `delta_report(prev: list[HolderPosition], cur: list[HolderPosition], top: int) -> dict`

- [ ] **Step 1: Failing test**

`backend/tests/test_analytics_holdings.py`:
```python
import pytest
from sonar.analytics.holdings import classify_delta, delta_report
from sonar.store.holdings_repo import HolderPosition


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_analytics_holdings.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.analytics.holdings`

- [ ] **Step 3: Implement**

```python
"""13F pozisyon matematiği — saf, market bilmez.

Opsiyon pozisyonları (put/call) hisse sayısına KARIŞTIRILMAZ: 13F'te ayrı satır olarak gelirler
ve "BofA 100M lot aldı" ile "BofA 2M lot PUT aldı" bambaşka şeylerdir (spec §7).
"""

from sonar.store.holdings_repo import HolderPosition


def classify_delta(prev_shares: int, cur_shares: int) -> str:
    if prev_shares == 0 and cur_shares > 0:
        return "new"
    if prev_shares > 0 and cur_shares == 0:
        return "exit"
    if cur_shares > prev_shares:
        return "add"
    if cur_shares < prev_shares:
        return "trim"
    return "hold"


def _long_by_cik(positions: list[HolderPosition]) -> dict[str, HolderPosition]:
    return {p.cik: p for p in positions if not p.put_call}


def delta_report(
    prev: list[HolderPosition], cur: list[HolderPosition], top: int = 10
) -> dict:
    prev_map = _long_by_cik(prev)
    cur_map = _long_by_cik(cur)

    movers = []
    for cik in prev_map.keys() | cur_map.keys():
        before = prev_map[cik].shares if cik in prev_map else 0
        after = cur_map[cik].shares if cik in cur_map else 0
        action = classify_delta(before, after)
        if action == "hold":
            continue
        holder = cur_map.get(cik) or prev_map[cik]
        movers.append({
            "cik": cik,
            "filer_name": holder.filer_name,
            "action": action,
            "shares": after,
            "delta_shares": after - before,
        })
    movers.sort(key=lambda m: abs(m["delta_shares"]), reverse=True)

    return {
        "total_shares": sum(p.shares for p in cur_map.values()),
        "filer_count": len(cur_map),
        "new": sum(1 for m in movers if m["action"] == "new"),
        "exit": sum(1 for m in movers if m["action"] == "exit"),
        "movers": movers[:top],
        "options": [
            {"filer_name": p.filer_name, "put_call": p.put_call, "shares": p.shares}
            for p in cur
            if p.put_call
        ],
    }
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_analytics_holdings.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: analytics/holdings — delta siniflamasi (new/exit/add/trim) + opsiyon ayrimi"
```

---

### Task B4: `get_institutional_holders` + `get_filer_holdings`

**Files:**
- Create: `backend/sonar/tools/holders.py`, `backend/sonar/market/us/cusip.py`
- Modify: `backend/sonar/market/us/__init__.py`, `backend/sonar/config.py`
- Test: `backend/tests/test_holders_tool.py`

**Interfaces:**
- Consumes: `HoldingsRepo` (B1), `delta_report` (B3)
- Produces: `CusipMap(conn).cusip_for(ticker) -> str | None` ·
  `get_institutional_holders(ticker, *, registry, cache, ttl) -> dict{..., provenance_note}` ·
  `get_filer_holdings(filer_cik, ...) -> dict`

- [ ] **Step 1: Failing test — dürüstlük notu ZORUNLU**

`backend/tests/test_holders_tool.py`:
```python
from sonar.store.holdings_repo import HoldingsRepo, Row
from sonar.market.us.cusip import CusipMap
from sonar.tools.holders import get_institutional_holders
from sonar.store.cache import Cache


def _seed(conn):
    repo = HoldingsRepo(conn)
    repo.ingest([Row("a", "1", "BERKSHIRE", "67066G104", "NVIDIA CORP", 500, 5000, "", "")], "2025Q4")
    repo.ingest(
        [
            Row("b", "1", "BERKSHIRE", "67066G104", "NVIDIA CORP", 0, 0, "", ""),
            Row("b", "2", "BOFA", "67066G104", "NVIDIA CORP", 1000, 10000, "", ""),
            Row("b", "2", "BOFA", "67066G104", "NVIDIA CORP", 200, 2000, "Put", ""),
        ],
        "2026Q1",
    )
    conn.execute("INSERT INTO cusip_ticker VALUES ('67066G104', 'NVDA')")
    conn.commit()
    return repo


def test_holders_returns_delta_and_options(conn):
    _seed(conn)
    out = get_institutional_holders("nvda", conn=conn, cache=Cache(conn), ttl=86400)
    assert out["quarter"] == "2026Q1"
    assert out["movers"][0]["filer_name"] == "BOFA"
    assert out["movers"][0]["action"] == "new"
    assert out["options"][0]["put_call"] == "Put"


def test_holders_carry_mandatory_provenance_note(conn):
    _seed(conn)
    out = get_institutional_holders("nvda", conn=conn, cache=Cache(conn), ttl=86400)
    note = out["provenance_note"]
    assert "13F" in note and "45 gün" in note
    assert "short" in note.lower() and "swap" in note.lower()  # verinin sınırı yazıyor


def test_unknown_ticker_returns_explicit_gap(conn):
    _seed(conn)
    out = get_institutional_holders("ZZZZ", conn=conn, cache=Cache(conn), ttl=86400)
    assert out["unavailable"]  # sessiz boş liste DEĞİL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_holders_tool.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.tools.holders`

- [ ] **Step 3: `market/us/cusip.py`**

```python
"""CUSIP ↔ ticker haritası. CUSIP lisanslı bir kimlik; SEC ücretsiz-resmî iki yol bırakıyor:
(i) fails-to-deliver dosyaları (CUSIP + SYMBOL birlikte), (ii) 13F issuer adı ↔ company_tickers.json.
Kapsam oranı B0 spike'ında ölçüldü — rapora bak."""

import sqlite3


class CusipMap:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def cusip_for(self, ticker: str) -> str | None:
        row = self._conn.execute(
            "SELECT cusip FROM cusip_ticker WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        return row[0] if row else None

    def ticker_for(self, cusip: str) -> str | None:
        row = self._conn.execute(
            "SELECT ticker FROM cusip_ticker WHERE cusip = ?", (cusip.upper(),)
        ).fetchone()
        return row[0] if row else None

    def load(self, pairs: list[tuple[str, str]]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO cusip_ticker (cusip, ticker) VALUES (?, ?)", pairs
        )
        self._conn.commit()
```

> **Haritanın doldurulması** B0'da seçilen yolla yapılır (FTD ZIP + isim eşleşmesi). Bunu
> `Ingester`'a bir adım olarak ekle: ZIP indirilirken CUSIP haritası da kurulur, `CusipMap.load()`
> ile yazılır. Kaynak URL'lerini B0 raporundan al.

- [ ] **Step 4: `tools/holders.py`**

```python
"""Big Players tool'ları.

Her çıktı DÜRÜSTLÜK NOTU taşır (spec §7): 13F 45 gün gecikmeli, yalnız long ABD hissesi + listed
opsiyon. Short ve swap ABD'de bildirilmiyor (Archegos boşluğu) — bu bir eksiklik değil, verinin sınırı.
Not dipnot değil, tool çıktısının parçası: LLM sentezinde de görünsün.
"""

import sqlite3

from sonar.analytics.holdings import delta_report
from sonar.market.us.cusip import CusipMap
from sonar.store.cache import Cache
from sonar.store.holdings_repo import HoldingsRepo
from sonar.tools._cache import cached

NOTE = (
    "13F · {quarter} · 45 gün gecikmeli · yalnız long ABD hissesi + listed opsiyon. "
    "Short ve swap görünmez — bu bir eksiklik değil, verinin sınırı."
)


def get_institutional_holders(
    ticker: str, *, conn: sqlite3.Connection, cache: Cache, ttl: int, top: int = 10
) -> dict:
    def compute() -> dict:
        cusip = CusipMap(conn).cusip_for(ticker)
        if cusip is None:
            return {"unavailable": f"{ticker.upper()}: CUSIP haritada yok (13F verisi eşleşmedi)"}
        repo = HoldingsRepo(conn)
        quarters = repo.quarters()
        if not quarters:
            return {"unavailable": "13F verisi henüz indirilmedi (/api/ingest/status)"}

        current = quarters[-1]
        previous = quarters[-2] if len(quarters) > 1 else None
        report = delta_report(
            repo.holders_of(cusip, previous) if previous else [],
            repo.holders_of(cusip, current),
            top=top,
        )
        return {
            "ticker": ticker.upper(),
            "quarter": current,
            "compared_to": previous,
            **report,
            "trend": repo.trend(cusip),
            "provenance_note": NOTE.format(quarter=current),
        }

    return cached(cache, f"holders:{ticker.upper()}", ttl, compute)


def get_filer_holdings(
    filer_cik: str, *, conn: sqlite3.Connection, cache: Cache, ttl: int
) -> dict:
    def compute() -> dict:
        repo = HoldingsRepo(conn)
        quarters = repo.quarters()
        if not quarters:
            return {"unavailable": "13F verisi henüz indirilmedi"}
        current = quarters[-1]
        return {
            "filer_cik": filer_cik,
            "quarter": current,
            "positions": repo.filer_holdings(filer_cik, current),
            "provenance_note": NOTE.format(quarter=current),
        }

    return cached(cache, f"filer:{filer_cik}", ttl, compute)
```

`config.py`: `HOLDERS_TTL_SECONDS = 86400`

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest -q`
Expected: 84 passed

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: get_institutional_holders + get_filer_holdings (delta + zorunlu durustluk notu)"
```

---

### Task B5: Form 4 (insider) + cluster tespiti

**Files:**
- Create: `backend/sonar/domain/insider.py`, `backend/sonar/analytics/insiders.py`,
  `backend/sonar/tools/insiders.py`
- Modify: `backend/sonar/market/us/edgar.py`, `backend/sonar/market/us/__init__.py`
- Test: `backend/tests/test_insiders.py`

**Interfaces:**
- Produces: `InsiderTrade(name, title, action, shares, price, traded_at)` ·
  `EdgarClient.insider_trades(symbol, days=90) -> list[InsiderTrade]` ·
  `cluster(trades, window_days=30) -> dict{buyers, sellers, is_cluster_buy}` ·
  `get_insider_trades(ticker, *, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test**

`backend/tests/test_insiders.py`:
```python
from sonar.analytics.insiders import cluster
from sonar.domain.insider import InsiderTrade

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_insiders.py -v`
Expected: FAIL — `ModuleNotFoundError: sonar.domain.insider`

- [ ] **Step 3: `domain/insider.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InsiderTrade:
    name: str
    title: str
    action: str       # "buy" | "sell"
    shares: int
    price: float | None
    traded_at: int    # unix saniye
```

- [ ] **Step 4: `analytics/insiders.py`**

```python
"""Insider cluster tespiti — saf matematik.

Tek yöneticinin alımı gürültüdür; AYNI pencerede BİRDEN FAZLA farklı yönetici açık piyasadan
alıyorsa haber vardır (cluster buying — ücretsiz veride bulunan en sağlam sinyallerden biri).
"""

import time
from typing import Callable

from sonar.domain.insider import InsiderTrade

MIN_CLUSTER_BUYERS = 2


def cluster(
    trades: list[InsiderTrade],
    window_days: int = 30,
    now: float | Callable[[], float] = time.time,
) -> dict:
    current = now() if callable(now) else now
    cutoff = current - window_days * 86400
    recent = [t for t in trades if t.traded_at >= cutoff]

    buyers = {t.name for t in recent if t.action == "buy"}
    sellers = {t.name for t in recent if t.action == "sell"}
    return {
        "window_days": window_days,
        "buyers": len(buyers),
        "sellers": len(sellers),
        "bought_shares": sum(t.shares for t in recent if t.action == "buy"),
        "sold_shares": sum(t.shares for t in recent if t.action == "sell"),
        "is_cluster_buy": len(buyers) >= MIN_CLUSTER_BUYERS and not sellers,
    }
```

- [ ] **Step 5: `edgar.py` — Form 4 çekimi**

```python
FORM4_INDEX = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"


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
                ARCHIVE.format(cik=int(cik), acc_nodash=acc.replace("-", ""), doc=doc)
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
```

> **Why sadece P ve S:** Form 4 kodlarının çoğu (A=hibe, M=opsiyon kullanımı, F=vergi kesintisi)
> **karar değil**, otomatik olaydır. "CEO hisse sattı" manşetlerinin çoğu aslında F kodudur (vergi için
> otomatik satış). Yalnız açık piyasa alım/satımı sinyal taşır.

- [ ] **Step 6: `tools/insiders.py` + plugin**

```python
from dataclasses import asdict

from sonar.analytics.insiders import cluster
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools._cache import cached

NOTE = "Form 4 · 2 iş günü gecikmeli · yalnız açık piyasa alım/satımı (hibe/vergi kesintisi hariç)."


def get_insider_trades(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)

    def compute() -> dict:
        trades = registry.get(symbol.market).get_insider_trades(symbol)
        return {
            "ticker": symbol.ticker,
            "trades": [asdict(t) for t in trades],
            "cluster": cluster(trades),
            "provenance_note": NOTE,
        }

    return cached(cache, f"insiders:{symbol.market}:{symbol.ticker}", ttl, compute)
```

`market/us/__init__.py`:
```python
    def get_insider_trades(self, symbol: Symbol):
        return self._edgar.insider_trades(symbol)
```

- [ ] **Step 7: Slow test — gerçek Form 4**

`backend/tests/test_insiders.py` sonuna:
```python
import pytest
from sonar.domain.symbol import Symbol
from sonar.market.us import _default_http
from sonar.market.us.edgar import EdgarClient


@pytest.mark.slow
def test_real_form4_parses():
    trades = EdgarClient(_default_http()).insider_trades(Symbol("NVDA", "US"), limit=3)
    assert all(t.action in ("buy", "sell") for t in trades)
```

- [ ] **Step 8: Run tests**

Run: `cd backend && uv run pytest -q && uv run pytest -m slow -q -k form4`
Expected: 88 passed · slow: 1 passed

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: Form 4 insider islemleri + cluster tespiti (yalniz acik piyasa P/S)"
```

---

### Task B6: `get_short_interest` — FINRA

> **Ön koşul:** B0 Step 7 hangi yolun çalıştığını söyledi. Key'siz FINRA dosyası varsa onu kullan;
> yoksa yfinance `.info` (`sharesShort`, `shortRatio`) ile **Provenance = "Yahoo (ikinci-el)"**.
> Her iki durumda da tool imzası ve çıktı şekli **aynıdır**.

**Files:**
- Create: `backend/sonar/market/us/finra.py`, `backend/sonar/tools/short_interest.py`
- Modify: `backend/sonar/market/us/__init__.py`, `backend/sonar/domain/holdings.py` (ShortInterest VO)
- Test: `backend/tests/test_short_interest.py`

**Interfaces:**
- Produces: `ShortInterest(symbol, shares_short, days_to_cover, as_of, source)` ·
  `get_short_interest(ticker, *, registry, cache, ttl) -> dict`

- [ ] **Step 1: Failing test — days-to-cover ÇEKİRDEKTE hesaplanır**

`backend/tests/test_short_interest.py`:
```python
from sonar.analytics.indicators import days_to_cover


def test_days_to_cover():
    assert days_to_cover(shares_short=1_000_000, avg_daily_volume=500_000) == 2.0


def test_days_to_cover_zero_volume_is_none():
    assert days_to_cover(shares_short=1_000_000, avg_daily_volume=0) is None
```

Ayrıca tool testi (fake plugin ile), `test_holders_tool.py` desenini izle: çıktıda
`shares_short`, `days_to_cover`, `source` ve **isimsizlik notu** olmalı:
```python
def test_short_interest_note_says_aggregate_no_names(conn):
    ...
    assert "toplam" in out["provenance_note"].lower()
    assert "kim" in out["provenance_note"].lower()  # "kimin short'ladığı bilinmiyor"
```

- [ ] **Step 2–5: Implement**

`analytics/indicators.py` sonuna:
```python
def days_to_cover(shares_short: int, avg_daily_volume: float) -> float | None:
    """Açık short pozisyonun kaç günlük hacme denk geldiği. Squeeze riskinin standart ölçüsü."""
    if not avg_daily_volume:
        return None
    return round(shares_short / avg_daily_volume, 2)
```

`market/us/finra.py` — B0'da doğrulanan yolu uygula. `tools/short_interest.py` — `_cache.cached`
deseniyle, çıktıya not ekle:
```python
NOTE = (
    "Short interest · FINRA · ayda 2 kez · TOPLAM rakam — kimin short'ladığı bilinmiyor "
    "(kurumsal short ABD'de bildirilmiyor)."
)
```
Days-to-cover için ortalama günlük hacim `get_ohlcv`'den gelir (son 20 bar) — `analytics`'te hesaplanır,
plugin'de değil.

- [ ] **Step 6: Run tests + Commit**

Run: `cd backend && uv run pytest -q`
```bash
git add backend/
git commit -m "feat: get_short_interest (FINRA) + days-to-cover — toplam rakam, isim yok"
```

---

### Task B7: Recipe'ye `big_players` bölümü + prompt

Faz A'nın kodu **değişmez**; `SECTIONS`'a bir eleman, prompt'a bir başlık eklenir.

**Files:**
- Modify: `backend/sonar/agent/recipes/deep_analysis.py`, `backend/sonar/agent/tools.py`
- Test: `backend/tests/test_deep_analysis.py`

**Interfaces:**
- Consumes: `get_institutional_holders` (B4), `get_insider_trades` (B5), `get_short_interest` (B6)

- [ ] **Step 1: Failing test — big_players bölümü + veri yokken düşmeme**

`backend/tests/test_deep_analysis.py` sonuna:
```python
def test_gather_includes_big_players_and_survives_missing_13f(conn):
    out = gather("NVDA", **_ctx(conn))
    assert "big_players" in out
    # 13F henüz indirilmemiş → bölüm "unavailable" ama rapor ayakta (Faz A bağımsız)
    assert out["big_players"]["unavailable"] or out["big_players"]["holders"]
```

- [ ] **Step 2: `SECTIONS` ve `gather`**

```python
SECTIONS = ("macro", "fundamentals", "technicals", "news", "peers", "big_players")
```
`gather`'a bölüm ekle (conn parametresi gerekiyor — `make_analyzer` ve `api/app.py` imzasına `conn` ekle):
```python
        "big_players": run("big_players", lambda: {
            "holders": get_institutional_holders(
                ticker, conn=conn, cache=cache, ttl=config.HOLDERS_TTL_SECONDS
            ),
            "insiders": get_insider_trades(ticker, **ctx, ttl=config.INSIDERS_TTL_SECONDS),
            "short_interest": get_short_interest(ticker, **ctx, ttl=config.SHORT_TTL_SECONDS),
        }),
```

- [ ] **Step 3: `SYNTHESIS_PROMPT` — bölüm 5 eklenir, sentez 6 olur**

```
  5. BÜYÜK OYUNCULAR — kurumlar ne yaptı (13F Δ: yeni giriş/çıkış/artırma/azaltma), yöneticiler
     ne yaptı (Form 4 cluster), toplam short konumlanma.
     ZORUNLU: her Big Players cümlesinin yanında provenance_note'taki gecikmeyi belirt
     ("13F, 45 gün gecikmeli"). Gecikmeli veriyi güncelmiş gibi anlatma.
     Short/swap görünmediğini SAKLAMA — "çıktı" demek yerine "13F'te göründüğü kadarıyla çıktı" de.
  6. SENTEZ — katmanlar birbirini destekliyor mu, çelişiyor mu? Ana risk ne?
```

- [ ] **Step 4: ReAct'e üç tool daha (`agent/tools.py`)**

`make_tools`'a `get_institutional_holders` (`conn` gerekiyor → `make_tools(*, registry, cache, conn)`),
`get_insider_trades`, `get_short_interest` ekle; `graph.py` ve `api/app.py` çağrılarını güncelle.
Toplam **10 tool**.

- [ ] **Step 5: Run tests + Commit**

Run: `cd backend && uv run pytest -q`
```bash
git add backend/
git commit -m "feat: recipe'ye big_players bolumu (13F delta + insider cluster + short) — Faz A kodu degismedi"
```

---

### Task B8: Frontend — Big Players paneli + ingest durumu

**Files:**
- Create: `frontend/src/bigplayers.tsx`
- Modify: `frontend/src/parts.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: `parts.tsx` — `analysis_step` etiketine `big_players` zaten var (SECTION_LABEL)**

Doğrula: `big_players: "Büyük oyuncular"` satırı `SECTION_LABEL`'da mevcut.

- [ ] **Step 2: `App.tsx` — ingest durumu şeridi**

```tsx
function IngestBanner() {
  const [state, setState] = useState<{ status: string; progress: number; quarter: string } | null>(null);
  useEffect(() => {
    const poll = () =>
      fetch("/api/ingest/status")
        .then((r) => r.json())
        .then(setState)
        .catch(() => {});
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);
  if (!state || state.status === "ready" || state.status === "idle") return null;
  const text =
    state.status === "error"
      ? "13F verisi indirilemedi — büyük oyuncular bölümü şu an yok."
      : `13F verisi indiriliyor (${state.quarter}) — %${Math.round(state.progress * 100)}`;
  return (
    <div style={{ padding: "6px 20px", background: "#12261f", color: "#7ee787", fontSize: 13 }}>
      {text}
    </div>
  );
}
```
`<SourceBanner />`'ın altına `<IngestBanner />` ekle.

- [ ] **Step 3: Build + elle doğrula**

```bash
cd frontend && npm run build
cd ../backend && uv run sonar
```
Tarayıcı → Derin Analiz → `NVDA`:
1. İlk açılışta "13F verisi indiriliyor" şeridi görünüyor
2. `✓ Büyük oyuncular` adımı geliyor
3. Rapor "13F, 45 gün gecikmeli" notunu **yazıyor**
4. Veri henüz inmediyse: rapor yine çıkıyor, o bölüm "veri yok" diyor

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: big players paneli + 13F ingest durum seridi"
```

---

## 🏁 FAZ B DoD

- [ ] `cd backend && uv run pytest -q` → **90+ passed**, 0 failed
- [ ] `uv run pytest -m slow -q` → gerçek EDGAR (companyfacts + Form 4) geçiyor
- [ ] **"NVDA'yı geçen çeyrek kim aldı/sattı"** → filer adı + Δ lot + aksiyon (new/exit/add/trim)
- [ ] Aynı sayı **EDGAR'da elle doğrulanıyor** (filer'ın 13F-HR belgesi ile karşılaştır)
- [ ] Her Big Players çıktısı **gecikme notunu** taşıyor; LLM raporunda da görünüyor
- [ ] Opsiyon (PUT/CALL) pozisyonları hisseye **karışmıyor**, ayrı gösteriliyor
- [ ] Amendment'lı bir çeyrekte Δ **saçmalamıyor** (RESTATEMENT satırları yerine geçmiş)
- [ ] Ham veri 2 çeyrek; `symbol_quarterly` trend satırları **duruyor** (prune sonrası)
- [ ] 13F verisi yokken derin analiz **yine çalışıyor** (Faz A bağımsız)

Kapı geçilince: ROADMAP'te **M2 ✅**, `NEXT_SESSION.md` güncellenir.

---

## Plan öz-denetimi (writing-plans)

**Spec kapsaması:** §2 veri gerçeği → B4/B5/B6 dürüstlük notları · §3 kaynaklar → A3/A7/A9/A10 ·
§4 mimari (Protocol+ABC, Strategy, composition, `_cache`) → A1/A3/A4 · §5 recipe → A11 ·
§6 API/SSE/grafik → A12/A13/A14/A16 · §7 Faz B (spike, depolama, amendment, PUTCALL) → B0/B1/B2/B3/B4 ·
§8 test stratejisi → her task'ta unit + `slow`; `test_layering` A5'te genişledi.

**Açık kalan (kasıtlı):** spec §7'deki *"eşleşmeyen CUSIP satırları atılsın mı"* kararı — **B0 spike'ı
ölçüp getirecek**, kullanıcı karar verecek (B0 Step 8/9).

**Tip tutarlılığı:** `Row`/`HolderPosition` (B1) → `delta_report` (B3) → `get_institutional_holders` (B4)
aynı alan adlarını kullanıyor. `PriceSource.quote/bars` (A1/A4) her iki implementasyonda aynı imza.
`quote-tick` sözleşmesi polling (A13) ve WS (A14) yollarında birebir aynı.
