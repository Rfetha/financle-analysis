# M0 — Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tek binary'den açılan web app, kullanıcı bir ticker yazar → gerçek fiyat gösterilir; tüm mimari katmanları (UI → FastAPI → tool → Market plugin/ACL → yfinance → SQLite cache) uçtan uca kanıtlanır. **LLM agent yok** (M1).

**Architecture:** Monorepo `backend/` (Python: FastAPI + raw sqlite3 + Market plugin) + `frontend/` (Vite+React). Backend deep tool `get_quote`'u bir `/api/quote/{ticker}` endpoint'i olarak sunar; React UI bunu çağırır. Yayında React build edilip FastAPI tarafından statik servis edilir; PyInstaller tek binary üretir. Market verisi `MarketPlugin` (Strategy) arkasında — US plugin yfinance'i domain VO'ya çevirir (ACL); sonuç SQLite cache'lenir (TTL).

**Tech Stack:** Python 3.12 · uv · FastAPI · uvicorn · httpx · yfinance · raw `sqlite3` · pytest · Vite · React · TypeScript · PyInstaller

## Global Constraints

- **Python ≥ 3.12**; paket/venv yönetimi **uv** (ADR-0006).
- **Store = tek SQLite dosyası**, WAL açık; Redis yok, ORM yok, vector DB yok (ADR-0004).
- **Deep tool:** tool hesaplanmış/yapılandırılmış sonuç (domain VO) döner, ham dış şekil değil (ADR-0003).
- **Market plugin = ACL:** dış kaynak (yfinance) ham şekli domain'e sızmaz; plugin VO'ya çevirir (ADR-0001/0005). Veremediği yetenek → `Unsupported` (çökmez).
- **Domain dili = CONTEXT.md** (Symbol, Money, Quote, Provenance, Market). Kod birebir bu isimleri kullanır.
- **Registry global değil:** uygulama başlangıcında kurulup enjekte edilir (test edilebilirlik; design-antipatterns).
- **Frontend çalıştırmada node gerektirmez:** build edilmiş statik FastAPI tarafından servis edilir; son kullanıcı tek binary çalıştırır (ADR-0001).
- **DB cache TTL'i:** quote için 60 sn.

## File Structure

```
backend/
  pyproject.toml                  uv projesi + deps
  sonar/
    __init__.py
    config.py                     ayarlar (db path, ttl)
    domain/
      __init__.py
      money.py                    Money VO (frozen)
      symbol.py                   Symbol VO (frozen)
      quote.py                    Quote VO (frozen) + Provenance
    store/
      __init__.py
      db.py                       sqlite bağlantı + WAL + şema
      cache.py                    Cache: get/set (TTL)
    market/
      __init__.py
      base.py                     MarketPlugin Protocol + Unsupported
      registry.py                 MarketRegistry (enjekte edilir)
      us.py                       USMarketPlugin.get_quote (yfinance → Quote)
    tools/
      __init__.py
      quote.py                    get_quote(ticker): cache + registry
    api/
      __init__.py
      app.py                      FastAPI: /api/quote/{ticker} + statik servis
    cli.py                        entrypoint: uvicorn + tarayıcı aç
  tests/
    conftest.py                   temp_db fixture
    test_domain.py
    test_cache.py
    test_us_plugin.py
    test_quote_tool.py
    test_api_quote.py
frontend/
  package.json
  index.html
  vite.config.ts                  dev'de /api → :8000 proxy
  tsconfig.json
  src/
    main.tsx
    App.tsx                       ticker input → fiyat göster
sonar.spec                        PyInstaller (root)
```

---

### Task 1: Backend project scaffold + health endpoint

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/sonar/__init__.py` (boş)
- Create: `backend/sonar/config.py`
- Create: `backend/sonar/api/__init__.py` (boş)
- Create: `backend/sonar/api/app.py`
- Test: `backend/tests/test_api_health.py`

**Interfaces:**
- Produces: `sonar.api.app.create_app() -> FastAPI` (uygulama fabrikası); `GET /api/health` → `{"status": "ok"}`.

- [ ] **Step 1: pyproject.toml yaz**

```toml
[project]
name = "sonar"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn>=0.30",
  "httpx>=0.27",
  "yfinance>=0.2.40",
]

[dependency-groups]
dev = ["pytest>=8", "pyinstaller>=6.5"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
markers = ["slow: gerçek dış ağ çağrısı (yfinance) — varsayılan koşuda atlanır"]
addopts = "-m 'not slow'"
```

- [ ] **Step 2: config.py yaz**

```python
import os
from pathlib import Path

DB_PATH = Path(os.environ.get("SONAR_DB", Path.home() / ".sonar" / "sonar.db"))
QUOTE_TTL_SECONDS = 60
```

- [ ] **Step 3: Failing test yaz**

`backend/tests/test_api_health.py`:
```python
from fastapi.testclient import TestClient
from sonar.api.app import create_app


def test_health_returns_ok():
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 4: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_api_health.py -v`
Expected: FAIL (`ModuleNotFoundError: sonar.api.app` / `create_app`).

- [ ] **Step 5: app.py minimal implementasyon**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Sonar")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

- [ ] **Step 6: Testi çalıştır, PASS gör**

Run: `cd backend && uv run pytest tests/test_api_health.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(m0): backend scaffold + /api/health"
```

---

### Task 2: Domain Value Objects (Money, Symbol, Quote)

**Files:**
- Create: `backend/sonar/domain/__init__.py` (boş)
- Create: `backend/sonar/domain/money.py`
- Create: `backend/sonar/domain/symbol.py`
- Create: `backend/sonar/domain/quote.py`
- Test: `backend/tests/test_domain.py`

**Interfaces:**
- Produces:
  - `Money(amount: Decimal, currency: str)` — frozen; `Money + Money` aynı currency, farklıysa `ValueError`.
  - `Symbol(ticker: str, market: str)` — frozen; `ticker` upper-case normalize (`__post_init__` ile `object.__setattr__`).
  - `Provenance(source: str, fetched_at: float)` — frozen.
  - `Quote(symbol: Symbol, price: Money, previous_close: Money, provenance: Provenance)` — frozen; `change_pct` property → float.

- [ ] **Step 1: Failing test yaz**

`backend/tests/test_domain.py`:
```python
from decimal import Decimal
import pytest
from sonar.domain.money import Money
from sonar.domain.symbol import Symbol
from sonar.domain.quote import Quote, Provenance


def test_money_add_same_currency():
    assert Money(Decimal("1.5"), "USD") + Money(Decimal("2.5"), "USD") == Money(Decimal("4.0"), "USD")


def test_money_add_currency_mismatch_raises():
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")


def test_symbol_uppercases_ticker():
    assert Symbol("aapl", "US").ticker == "AAPL"


def test_quote_change_pct():
    q = Quote(
        symbol=Symbol("AAPL", "US"),
        price=Money(Decimal("110"), "USD"),
        previous_close=Money(Decimal("100"), "USD"),
        provenance=Provenance("yfinance", 0.0),
    )
    assert q.change_pct == pytest.approx(10.0)
```

- [ ] **Step 2: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_domain.py -v`
Expected: FAIL (import errors).

- [ ] **Step 3: money.py yaz**

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} != {other.currency}")
        return Money(self.amount + other.amount, self.currency)
```

- [ ] **Step 4: symbol.py yaz**

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    ticker: str
    market: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", self.ticker.upper())
```

- [ ] **Step 5: quote.py yaz**

```python
from dataclasses import dataclass
from sonar.domain.money import Money
from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str
    fetched_at: float


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: Symbol
    price: Money
    previous_close: Money
    provenance: Provenance

    @property
    def change_pct(self) -> float:
        prev = self.previous_close.amount
        if prev == 0:
            return 0.0
        return float((self.price.amount - prev) / prev * 100)
```

- [ ] **Step 6: Testi çalıştır, PASS gör**

Run: `cd backend && uv run pytest tests/test_domain.py -v`
Expected: PASS (4 test).

- [ ] **Step 7: Commit**

```bash
git add backend/sonar/domain backend/tests/test_domain.py
git commit -m "feat(m0): domain VOs — Money, Symbol, Quote"
```

---

### Task 3: SQLite store + Cache (TTL)

**Files:**
- Create: `backend/sonar/store/__init__.py` (boş)
- Create: `backend/sonar/store/db.py`
- Create: `backend/sonar/store/cache.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_cache.py`

**Interfaces:**
- Produces:
  - `db.connect(path: Path) -> sqlite3.Connection` — WAL açar, şemayı (idempotent) kurar.
  - `Cache(conn)` — `get(key: str) -> str | None` (süresi geçen None), `set(key: str, value: str, ttl_seconds: int) -> None`.
- Consumes: `now: Callable[[], float]` enjekte edilebilir (test için); default `time.time`.

- [ ] **Step 1: conftest.py yaz**

`backend/tests/conftest.py`:
```python
import sqlite3
import pytest
from sonar.store.db import connect


@pytest.fixture()
def conn(tmp_path) -> sqlite3.Connection:
    c = connect(tmp_path / "test.db")
    yield c
    c.close()
```

- [ ] **Step 2: Failing test yaz**

`backend/tests/test_cache.py`:
```python
from sonar.store.cache import Cache


def test_cache_miss_returns_none(conn):
    assert Cache(conn).get("k") is None


def test_cache_set_then_get(conn):
    cache = Cache(conn)
    cache.set("k", "v", ttl_seconds=60)
    assert cache.get("k") == "v"


def test_cache_expired_returns_none(conn):
    clock = {"t": 1000.0}
    cache = Cache(conn, now=lambda: clock["t"])
    cache.set("k", "v", ttl_seconds=60)
    clock["t"] = 1061.0
    assert cache.get("k") is None
```

- [ ] **Step 3: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_cache.py -v`
Expected: FAIL (import error).

- [ ] **Step 4: db.py yaz**

```python
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  expires_at REAL NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn
```

- [ ] **Step 5: cache.py yaz**

```python
import sqlite3
import time
from typing import Callable


class Cache:
    def __init__(self, conn: sqlite3.Connection, now: Callable[[], float] = time.time) -> None:
        self._conn = conn
        self._now = now

    def get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None or row[1] <= self._now():
            return None
        return row[0]

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO cache(key, value, expires_at) VALUES (?, ?, ?)",
            (key, value, self._now() + ttl_seconds),
        )
        self._conn.commit()
```

- [ ] **Step 6: Testi çalıştır, PASS gör**

Run: `cd backend && uv run pytest tests/test_cache.py -v`
Expected: PASS (3 test).

- [ ] **Step 7: Commit**

```bash
git add backend/sonar/store backend/tests/conftest.py backend/tests/test_cache.py
git commit -m "feat(m0): SQLite store (WAL) + TTL cache"
```

---

### Task 4: MarketPlugin Protocol + Registry

**Files:**
- Create: `backend/sonar/market/__init__.py` (boş)
- Create: `backend/sonar/market/base.py`
- Create: `backend/sonar/market/registry.py`
- Test: `backend/tests/test_registry.py`

**Interfaces:**
- Produces:
  - `class Unsupported(Exception)` — bir market bir yeteneği veremezse.
  - `MarketPlugin` Protocol: `market: str`; `get_quote(self, symbol: Symbol) -> Quote`.
  - `MarketRegistry` — `register(plugin: MarketPlugin)`, `get(market: str) -> MarketPlugin` (yoksa `KeyError`).

- [ ] **Step 1: Failing test yaz**

`backend/tests/test_registry.py`:
```python
import pytest
from sonar.market.registry import MarketRegistry
from sonar.market.base import Unsupported


class _FakePlugin:
    market = "US"
    def get_quote(self, symbol):
        raise Unsupported("no quote")


def test_registry_get_returns_registered_plugin():
    reg = MarketRegistry()
    p = _FakePlugin()
    reg.register(p)
    assert reg.get("US") is p


def test_registry_unknown_market_raises():
    with pytest.raises(KeyError):
        MarketRegistry().get("TR")
```

- [ ] **Step 2: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_registry.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: base.py yaz**

```python
from typing import Protocol, runtime_checkable
from sonar.domain.symbol import Symbol
from sonar.domain.quote import Quote


class Unsupported(Exception):
    """Market bu yeteneği sağlayamıyor."""


@runtime_checkable
class MarketPlugin(Protocol):
    market: str

    def get_quote(self, symbol: Symbol) -> Quote: ...
```

- [ ] **Step 4: registry.py yaz**

```python
from sonar.market.base import MarketPlugin


class MarketRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, MarketPlugin] = {}

    def register(self, plugin: MarketPlugin) -> None:
        self._plugins[plugin.market] = plugin

    def get(self, market: str) -> MarketPlugin:
        return self._plugins[market]
```

- [ ] **Step 5: Testi çalıştır, PASS gör**

Run: `cd backend && uv run pytest tests/test_registry.py -v`
Expected: PASS (2 test).

- [ ] **Step 6: Commit**

```bash
git add backend/sonar/market/base.py backend/sonar/market/registry.py backend/tests/test_registry.py
git commit -m "feat(m0): MarketPlugin protocol + registry (Strategy)"
```

---

### Task 5: US plugin — get_quote (yfinance → Quote, ACL)

**Files:**
- Create: `backend/sonar/market/us.py`
- Test: `backend/tests/test_us_plugin.py`

**Interfaces:**
- Consumes: `MarketPlugin` protocol, `Symbol`, `Quote`, `Money`, `Provenance`.
- Produces: `USMarketPlugin(now=time.time, fetch=...)` — `market="US"`; `get_quote(symbol) -> Quote`. `fetch(ticker) -> tuple[float, float]` (last_price, previous_close) enjekte edilebilir (test); default yfinance.

- [ ] **Step 1: Failing test yaz (yfinance stub'lu — deterministik)**

`backend/tests/test_us_plugin.py`:
```python
from decimal import Decimal
import pytest
from sonar.market.us import USMarketPlugin
from sonar.domain.symbol import Symbol


def test_us_get_quote_builds_domain_quote():
    plugin = USMarketPlugin(now=lambda: 123.0, fetch=lambda ticker: (110.0, 100.0))
    q = plugin.get_quote(Symbol("AAPL", "US"))
    assert q.symbol == Symbol("AAPL", "US")
    assert q.price.amount == Decimal("110.0")
    assert q.previous_close.amount == Decimal("100.0")
    assert q.provenance.source == "yfinance"
    assert q.provenance.fetched_at == 123.0
    assert q.change_pct == pytest.approx(10.0)


@pytest.mark.slow
def test_us_get_quote_real_yfinance():
    q = USMarketPlugin().get_quote(Symbol("AAPL", "US"))
    assert q.price.amount > 0
```

- [ ] **Step 2: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_us_plugin.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: us.py yaz**

```python
import time
from decimal import Decimal
from typing import Callable
from sonar.domain.symbol import Symbol
from sonar.domain.money import Money
from sonar.domain.quote import Quote, Provenance


def _yfinance_fetch(ticker: str) -> tuple[float, float]:
    import yfinance as yf
    info = yf.Ticker(ticker).fast_info
    return float(info["lastPrice"]), float(info["previousClose"])


class USMarketPlugin:
    market = "US"

    def __init__(
        self,
        now: Callable[[], float] = time.time,
        fetch: Callable[[str], tuple[float, float]] = _yfinance_fetch,
    ) -> None:
        self._now = now
        self._fetch = fetch

    def get_quote(self, symbol: Symbol) -> Quote:
        last, prev = self._fetch(symbol.ticker)
        return Quote(
            symbol=symbol,
            price=Money(Decimal(str(last)), "USD"),
            previous_close=Money(Decimal(str(prev)), "USD"),
            provenance=Provenance("yfinance", self._now()),
        )
```

- [ ] **Step 4: Testi çalıştır, PASS gör (slow atlanır)**

Run: `cd backend && uv run pytest tests/test_us_plugin.py -v`
Expected: PASS (1 test; `_real_yfinance` deselected by `-m 'not slow'`).

- [ ] **Step 5: (opsiyonel) Gerçek yfinance teyidi**

Run: `cd backend && uv run pytest tests/test_us_plugin.py -m slow -v`
Expected: PASS (ağ varsa; gerçek AAPL fiyatı > 0).

- [ ] **Step 6: Commit**

```bash
git add backend/sonar/market/us.py backend/tests/test_us_plugin.py
git commit -m "feat(m0): US market plugin get_quote (yfinance ACL)"
```

---

### Task 6: get_quote tool (cache + registry)

**Files:**
- Create: `backend/sonar/tools/__init__.py` (boş)
- Create: `backend/sonar/tools/quote.py`
- Test: `backend/tests/test_quote_tool.py`

**Interfaces:**
- Consumes: `MarketRegistry`, `Cache`, `Symbol`, `Quote`.
- Produces: `get_quote(ticker: str, *, registry, cache, ttl: int, market="US") -> dict` — cache hit ise cache'ten, değilse plugin'den çekip cache'ler. Dönüş: `{"ticker", "price", "change_pct", "currency", "source"}` (JSON-uyumlu; deep tool — hesaplanmış change_pct dahil).

- [ ] **Step 1: Failing test yaz**

`backend/tests/test_quote_tool.py`:
```python
from decimal import Decimal
from sonar.tools.quote import get_quote
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.store.cache import Cache


def _registry():
    reg = MarketRegistry()
    reg.register(USMarketPlugin(now=lambda: 1.0, fetch=lambda t: (110.0, 100.0)))
    return reg


def test_get_quote_returns_computed_dict(conn):
    out = get_quote("aapl", registry=_registry(), cache=Cache(conn), ttl=60)
    assert out["ticker"] == "AAPL"
    assert out["price"] == "110.0"
    assert out["change_pct"] == 10.0
    assert out["currency"] == "USD"
    assert out["source"] == "yfinance"


def test_get_quote_second_call_hits_cache(conn):
    calls = {"n": 0}
    def fetch(t):
        calls["n"] += 1
        return (110.0, 100.0)
    reg = MarketRegistry()
    reg.register(USMarketPlugin(now=lambda: 1.0, fetch=fetch))
    cache = Cache(conn, now=lambda: 1.0)
    get_quote("AAPL", registry=reg, cache=cache, ttl=60)
    get_quote("AAPL", registry=reg, cache=cache, ttl=60)
    assert calls["n"] == 1  # ikinci çağrı cache'ten
```

- [ ] **Step 2: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_quote_tool.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: quote.py yaz**

```python
import json
from sonar.domain.symbol import Symbol
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache


def get_quote(
    ticker: str, *, registry: MarketRegistry, cache: Cache, ttl: int, market: str = "US"
) -> dict:
    symbol = Symbol(ticker, market)
    key = f"quote:{symbol.market}:{symbol.ticker}"
    cached = cache.get(key)
    if cached is not None:
        return json.loads(cached)

    quote = registry.get(symbol.market).get_quote(symbol)
    out = {
        "ticker": symbol.ticker,
        "price": str(quote.price.amount),
        "currency": quote.price.currency,
        "change_pct": round(quote.change_pct, 2),
        "source": quote.provenance.source,
    }
    cache.set(key, json.dumps(out), ttl)
    return out
```

- [ ] **Step 4: Testi çalıştır, PASS gör**

Run: `cd backend && uv run pytest tests/test_quote_tool.py -v`
Expected: PASS (2 test).

- [ ] **Step 5: Commit**

```bash
git add backend/sonar/tools backend/tests/test_quote_tool.py
git commit -m "feat(m0): get_quote tool (cache + registry)"
```

---

### Task 7: FastAPI /api/quote/{ticker} endpoint + wiring

**Files:**
- Modify: `backend/sonar/api/app.py`
- Test: `backend/tests/test_api_quote.py`

**Interfaces:**
- Consumes: `get_quote` tool, `MarketRegistry`, `USMarketPlugin`, `Cache`, `connect`, `config`.
- Produces: `create_app(registry=None, cache=None)` — bağımlılıklar enjekte edilebilir (test); default'ta gerçek SQLite + US plugin kurar. `GET /api/quote/{ticker}` → `get_quote` çıktısı (JSON). Bilinmeyen market → 422.

- [ ] **Step 1: Failing test yaz**

`backend/tests/test_api_quote.py`:
```python
from fastapi.testclient import TestClient
from sonar.api.app import create_app
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.store.cache import Cache
from sonar.store.db import connect


def _client(tmp_path):
    reg = MarketRegistry()
    reg.register(USMarketPlugin(now=lambda: 1.0, fetch=lambda t: (110.0, 100.0)))
    cache = Cache(connect(tmp_path / "t.db"), now=lambda: 1.0)
    return TestClient(create_app(registry=reg, cache=cache))


def test_quote_endpoint_returns_computed_quote(tmp_path):
    resp = _client(tmp_path).get("/api/quote/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert body["change_pct"] == 10.0
```

- [ ] **Step 2: Testi çalıştır, FAIL gör**

Run: `cd backend && uv run pytest tests/test_api_quote.py -v`
Expected: FAIL (`create_app` argüman almıyor / route yok).

- [ ] **Step 3: app.py güncelle**

```python
from fastapi import FastAPI
from sonar import config
from sonar.store.db import connect
from sonar.store.cache import Cache
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.tools.quote import get_quote


def _default_registry() -> MarketRegistry:
    reg = MarketRegistry()
    reg.register(USMarketPlugin())
    return reg


def create_app(registry: MarketRegistry | None = None, cache: Cache | None = None) -> FastAPI:
    app = FastAPI(title="Sonar")
    registry = registry or _default_registry()
    cache = cache or Cache(connect(config.DB_PATH))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/quote/{ticker}")
    def quote(ticker: str) -> dict:
        return get_quote(ticker, registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS)

    return app
```

- [ ] **Step 4: Testi çalıştır, PASS gör**

Run: `cd backend && uv run pytest tests/ -v`
Expected: PASS (tüm testler; health + domain + cache + registry + plugin + tool + api).

- [ ] **Step 5: Commit**

```bash
git add backend/sonar/api/app.py backend/tests/test_api_quote.py
git commit -m "feat(m0): /api/quote/{ticker} endpoint + DI wiring"
```

---

### Task 8: Frontend (Vite + React) — ticker → fiyat

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `GET /api/quote/{ticker}` → `{ticker, price, currency, change_pct, source}`.
- Produces: build çıktısı `frontend/dist/` (Task 9 bunu kullanır).

- [ ] **Step 1: package.json yaz**

```json
{
  "name": "sonar-frontend",
  "private": true,
  "type": "module",
  "scripts": { "dev": "vite", "build": "vite build" },
  "dependencies": { "react": "^18.3.0", "react-dom": "^18.3.0" },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: vite.config.ts yaz (dev'de /api proxy)**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
```

- [ ] **Step 3: tsconfig.json + index.html + main.tsx yaz**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020", "module": "ESNext", "moduleResolution": "bundler",
    "jsx": "react-jsx", "strict": true, "skipLibCheck": true
  },
  "include": ["src"]
}
```

`frontend/index.html`:
```html
<!doctype html>
<html><head><meta charset="utf-8" /><title>Sonar</title></head>
<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
```

`frontend/src/main.tsx`:
```tsx
import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(<App />);
```

- [ ] **Step 4: App.tsx yaz**

```tsx
import { useState } from "react";

type Quote = { ticker: string; price: string; currency: string; change_pct: number; source: string };

export function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function lookup() {
    setError(null);
    setQuote(null);
    const resp = await fetch(`/api/quote/${encodeURIComponent(ticker)}`);
    if (!resp.ok) { setError(`hata: ${resp.status}`); return; }
    setQuote(await resp.json());
  }

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 480, margin: "40px auto" }}>
      <h1>Sonar</h1>
      <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="AAPL" />
      <button onClick={lookup}>Fiyat</button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {quote && (
        <p>
          <b>{quote.ticker}</b>: {quote.price} {quote.currency}{" "}
          <span style={{ color: quote.change_pct >= 0 ? "green" : "crimson" }}>
            ({quote.change_pct >= 0 ? "+" : ""}{quote.change_pct}%)
          </span>{" "}
          <small>· {quote.source}</small>
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Dev'de uçtan uca dene (manuel verify)**

Terminal 1: `cd backend && uv run uvicorn sonar.api.app:create_app --factory --port 8000`
Terminal 2: `cd frontend && npm install && npm run dev`
Tarayıcı: Vite URL'i (`http://localhost:5173`) → "AAPL" → **Fiyat** → gerçek fiyat görünür.
Expected: fiyat + yüzde gösterilir (yfinance ağ erişimi gerekir).

- [ ] **Step 6: Build çalışır mı?**

Run: `cd frontend && npm run build`
Expected: `frontend/dist/` oluşur (index.html + assets).

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(m0): frontend (Vite+React) ticker→fiyat UI"
```

---

### Task 9: FastAPI statik servis + CLI entrypoint

**Files:**
- Modify: `backend/sonar/api/app.py`
- Create: `backend/sonar/cli.py`
- Modify: `backend/pyproject.toml` (script entry)

**Interfaces:**
- Consumes: `frontend/dist/` build çıktısı (build-zamanı `backend/sonar/web/static/`'e kopyalanır).
- Produces: `sonar` konsol komutu → uvicorn'u başlatır + tarayıcı açar. API yoksa SPA `index.html` döner.

- [ ] **Step 1: Build çıktısını paketin içine kopyala**

Run:
```bash
cd frontend && npm run build
mkdir -p ../backend/sonar/web/static
cp -r dist/* ../backend/sonar/web/static/
```
(Not: CI'da bu adım otomatik — bkz. Task 10 sonrası. Şimdilik elle.)

- [ ] **Step 2: app.py'a statik mount ekle (API route'lardan SONRA)**

`create_app` içinde, return'den hemen önce:
```python
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
```

- [ ] **Step 3: Statik servis testi yaz ve çalıştır**

`backend/tests/test_static.py`:
```python
from pathlib import Path
from fastapi.testclient import TestClient
from sonar.api.app import create_app


def test_root_serves_index_when_static_exists():
    static = Path(__file__).parent.parent / "sonar" / "web" / "static" / "index.html"
    client = TestClient(create_app())
    resp = client.get("/")
    if static.exists():
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
    else:
        assert resp.status_code in (404, 200)  # build yapılmadıysa tolere et
```

Run: `cd backend && uv run pytest tests/test_static.py -v`
Expected: PASS.

- [ ] **Step 4: cli.py yaz**

```python
import threading
import webbrowser
import uvicorn
from sonar.api.app import create_app


def main() -> None:
    port = 8000
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: pyproject.toml'a script ekle**

`[project]` altına:
```toml
[project.scripts]
sonar = "sonar.cli:main"
```

- [ ] **Step 6: Tek-process uçtan uca dene (manuel verify)**

Run: `cd backend && uv run sonar`
Expected: tarayıcı `http://127.0.0.1:8000` açılır, React UI gelir, "AAPL" → fiyat. **Tek process, Vite yok.**

- [ ] **Step 7: Commit**

```bash
git add backend/sonar/api/app.py backend/sonar/cli.py backend/pyproject.toml backend/tests/test_static.py
git commit -m "feat(m0): serve built frontend + sonar CLI entrypoint"
```

---

### Task 10: PyInstaller tek binary

**Files:**
- Create: `sonar.spec` (repo kökü)
- Create: `backend/sonar/web/__init__.py` (boş; paket olarak görünsün)

**Interfaces:**
- Consumes: `backend/sonar/web/static/` (Task 9'da kopyalanmış build), `sonar.cli:main`.
- Produces: `dist/sonar` (tek çalıştırılabilir).

- [ ] **Step 1: Build statiğin yerinde olduğunu doğrula**

Run: `ls backend/sonar/web/static/index.html`
Expected: dosya var (yoksa Task 9 Step 1'i tekrar çalıştır).

- [ ] **Step 2: sonar.spec yaz**

```python
# sonar.spec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("backend/sonar/web/static", "sonar/web/static")]
hiddenimports = collect_submodules("yfinance") + collect_submodules("uvicorn")

a = Analysis(
    ["backend/sonar/cli.py"],
    pathex=["backend"],
    datas=datas,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="sonar", console=True)
```

- [ ] **Step 3: Binary'yi derle**

Run: `uv run pyinstaller sonar.spec --noconfirm`
Expected: `dist/sonar` (Win'de `dist/sonar.exe`) oluşur.

- [ ] **Step 4: Binary'yi çalıştır (manuel verify — M0 kabul testi)**

Run: `./dist/sonar` (Win: `dist\sonar.exe`)
Expected: tarayıcı açılır → React UI → "AAPL" → **gerçek fiyat**. Python/Node kurulu olmasa da çalışır.

- [ ] **Step 5: Commit**

```bash
git add sonar.spec backend/sonar/web/__init__.py
git commit -m "feat(m0): PyInstaller single binary build"
```

---

## M0 Kabul Kriteri (Definition of Done)

1. `uv run pytest` → tüm unit testler yeşil (slow hariç).
2. `uv run sonar` → tek process, tarayıcı açılır, "AAPL" → gerçek fiyat + yüzde.
3. `dist/sonar` binary'si → Python/Node olmadan aynı deneyim.
4. Katmanların hepsi gerçek kodla bağlı: React → FastAPI → tool → MarketPlugin(ACL) → yfinance → SQLite cache.

## Notlar / sonraki milestone

- **M1:** LangGraph `create_react_agent` + `/api/chat` (SSE) — `get_quote` tool'unu agent'a bağla; UI'a chat kutusu. (Bu plan kapsamı dışı.)
- M0'da kasıtlı yok: LLM, ek tool'lar, portföy, otonomi, OAuth, MCP server.
