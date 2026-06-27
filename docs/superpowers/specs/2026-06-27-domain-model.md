# Sonar — Domain Model (DDD)

> Aggregate / Value Object / sınır kararları. Dil kaynağı: `CONTEXT.md`. Karar kaydı: ADR-0005.
> Tarih: 2026-06-27

## Bounded Context
Tek context (Sonar), modüler. Solo OSS app → çoklu bounded-context overkill (YAGNI).
Tek ubiquitous language = `CONTEXT.md`. **Tek gerçek sınır = Market plugin =
Anti-Corruption Layer:** dış kaynak (EDGAR/yfinance/FRED) ham şekilleri domain'e sızmaz;
plugin domain VO'larına çevirir. (ADR-0001 "tool'lar sabit, borsalar plugin"in DDD karşılığı.)

## Aggregate vs dış olgu
- **Sahip olup mutate ettiğimiz → Aggregate** (invariant'lı).
- **Dış olgu** (fiyat/temel/ham holder) → **Value Object**, Market ACL arkası, cache'lenir,
  asla mutate edilmez. Bu ayrım aggregate sayısını küçük tutar.

## Aggregate'ler

### Portfolio
- Root: **Portfolio**. İçinde entity: **Position** {Symbol, Quantity, avg_cost: Money}.
- Erişim yalnız root'tan: `portfolio.add_position()` / `.update_lot()` / `.remove()`.
  Dışarıdan `portfolio._positions.append(...)` yok.
- Invariant: sembol başına **tek** Position; Quantity ≥ 0; ağırlık/konsantrasyon
  Position'lardan **türetilir** (saklanmaz).
- v1: tek `avg_cost`. **FIFO lot + realized P&L = v2.**
- Repo: `PortfolioRepository`.

### Watchlist
- Root: **Watchlist**. Entry: **WatchEntry** {Symbol, added_at}.
- Invariant: Symbol tekrarsız.
- Repo: `WatchlistRepository`.

### Alert
- Root: **Alert** {condition, cooldown, last_triggered_at, enabled}. Her Alert bağımsız aggregate.
- Invariant: cooldown içindeyken yeniden tetiklenmez.
- Repo: `AlertRepository`.

### HoldingsSnapshot — append-only, **immutable**
- Root: **HoldingsSnapshot** {Filer, Period, list[HolderPosition]}.
- filer × period benzersiz; bir kez yazılır, değişmez (filing immutable).
- Δ (yeni/artan/azalan/kapanan) iki snapshot'tan **analytics** ile hesaplanır — **saklanmaz**.
- Repo: `HoldingsSnapshotRepository`.

### InsiderTrade — append-only, **immutable** event
- {Symbol, insider, txn_type, Quantity, price: Money, date}. Tek olay; event-log'a eklenir.
- Repo: `InsiderTradeRepository`.

### Brief — append-only, **immutable**
- {date, sections[], items[]}; o sabahın fotoğrafı, bir kez üretilir.
- Repo: `BriefRepository`.

### DeepAnalysis — aggregate **değil**
- Tool'lardan derlenen transient çıktı; default saklanmaz (opsiyonel artefakt).

## Value Objects (`frozen`, identity yok)
| VO | İçerik |
|---|---|
| **Symbol** | ticker + Market — ham `str` değil (Primitive Obsession fix) |
| **Money** | amount + currency(USD) — aritmetik + currency-match invariant |
| **Quantity** | Decimal ≥ 0 |
| **Percentage** | ağırlık / değişim / getiri |
| **Period** | yıl + çeyrek (2026Q1) |
| **DateRange** | from / to (OHLCV aralığı) |
| **Signal** | value ∈ [-1, +1] + label |
| **HolderPosition** | Symbol + Quantity + Money + Percentage (snapshot içi) |
| **Provenance** | source + fetched_at (her dış veriye iliştirilir) |
| **Quote · OhlcvSeries · Fundamentals** | Market ACL read-model çıktıları |

## Repository kuralı (rfetha-data-access)
Aggregate başına **bir** repository. Market data repo **değil** → plugin (ACL) + cache.
Hepsi SQLite (ADR-0004).

## SQLite tablo izdüşümü (özet)
```
portfolio / position
watchlist / watch_entry
alert
holdings_snapshot / holder_position      ← append-only
insider_trade                            ← append-only
brief                                    ← append-only
cache(key, value, expires_at)            ← Kova 1 (TTL)
FTS5 virtual table                       ← news/filing text
```
