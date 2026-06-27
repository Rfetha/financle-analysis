# 0005 — Aggregate sınırları; market data aggregate değil (ACL arkası VO)

Sonar'ın aggregate'leri **yalnız sahip olup mutate ettiğimiz** şeyler: **Portfolio**
(Position'ları içinde), **Watchlist**, **Alert**, ve append-only immutable kayıtlar
**HoldingsSnapshot / InsiderTrade / Brief**. **Dış piyasa verisi (fiyat, temel, ham
holder) aggregate DEĞİLDİR** — Market plugin (Anti-Corruption Layer) arkasında immutable
Value Object'tir, cache'lenir, asla mutate edilmez. 13F Δ ve P&L gibi türetilmiş değerler
**saklanmaz**, analytics ile hesaplanır.

## Consequences
- **Sürpriz uyarısı:** bir geliştirici Quote/Fundamentals'ı entity/aggregate yapmaya
  kalkabilir → bilinçli olarak hayır (dış olgu, bizim invariant'ımız yok).
- Aggregate başına **bir** repository; market data için repo yok (plugin + cache).
- Δ/P&L saklanmaz → tek doğruluk kaynağı = snapshot'lar + canlı fiyat; tutarsız türetilmiş
  veri riski ortadan kalkar.
- Aggregate kümesi küçük kalır → transaction sınırları net, SQLite'ta basit şema.
