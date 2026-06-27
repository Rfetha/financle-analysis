# Sonar

> US-equity araştırma & portföy asistanı — açık kaynak, provider-bağımsız, otonom çalışabilir.

**Durum:** erken geliştirme. Şu an **M0 (walking skeleton)** — tek binary, ticker → gerçek
fiyat. Tüm yol haritası: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Ne yapar (vizyon)

- **Tek hisse derin analiz:** makro + mikro/temel + teknik + **büyük oyuncular** (SEC 13F
  kurumsal + Form 4 insider) + haber → tek rapor + grafik.
- **Portföy & watchlist:** canlı değer, P&L, konsantrasyon riski, hızlı sinyaller.
- **Otonom günlük brief & alert:** her sabah senin hisselerine özel özet.
- **Chat:** "geçen çeyrek TSLA'yı en çok kim aldı?" → veriye dayalı, halüsinasyonsuz cevap.

ABD odaklı (hisse + ETF). Veri bedava/resmî kaynaklardan (yfinance · SEC EDGAR · FRED).

## Çalıştır

**Binary (önerilen, yakında):** `sonar.exe` (Win) / binary (Mac/Linux) indir → çalıştır →
tarayıcı açılır. Python/Node gerektirmez.

**Kaynaktan:**
```bash
cd backend && uv sync && uv run sonar     # tarayıcı http://127.0.0.1:8000 açılır
```
(uv kurulu olmalı: https://docs.astral.sh/uv/)

## Beyin (AI) sağlama

Tek, değiştirilebilir provider — kullanıcı seçer: **ChatGPT/Codex OAuth** · **Claude**
(Claude Code/MCP üzerinden) · **API key** (Anthropic/OpenAI). Aboneliğin yoksa API key yeter.

## Geliştirme

[`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, testler, dev-server, binary build, katkı akışı.

## Mimari & kararlar

- Vizyon/use-case: [spec](docs/superpowers/specs/2026-06-27-financle-us-equity-agent-design.md)
- Domain modeli (DDD): [domain-model](docs/superpowers/specs/2026-06-27-domain-model.md)
- Mimari kararlar: [`docs/adr/`](docs/adr/) (tool=plugin, derin tool, tek SQLite, LangGraph, uniform SSE…)
- Ubiquitous language: [`CONTEXT.md`](CONTEXT.md)

**Genişletilebilirlik:** borsalar **plugin**. v1 = US; başkaları aynı `MarketPlugin`
arayüzüyle BIST/crypto ekleyebilir — çekirdek değişmez.

## Lisans

_TBD_ — bkz. `LICENSE` (seçilecek).

## Sorumluluk reddi

Sonar bilgi + analiz üretir; **yatırım tavsiyesi değildir**. Karar kullanıcınındır. Emir
iletmez (al-sat yapmaz).
