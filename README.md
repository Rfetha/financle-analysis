# Sonar

> US-equity araştırma & portföy asistanı — açık kaynak, provider-bağımsız, otonom çalışabilir.

**Durum:** erken geliştirme. **M1 (agent omurgası)** tamam — chat'ten sorup token-token akan
cevap, araç adımları görünür. Tüm yol haritası: [`docs/ROADMAP.md`](docs/ROADMAP.md).

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

Tek model, tek loop (LangGraph). Model `SONAR_MODEL="<provider>:<model>"` ile seçilir:

| provider | örnek | endpoint | key |
|---|---|---|---|
| `local` **(varsayılan)** | `local:qwen3-14b` | `http://localhost:8080/v1` (llama-server) | yok |
| `openrouter` | `openrouter:anthropic/claude-sonnet-4.6` | OpenRouter | `OPENROUTER_API_KEY` |
| `anthropic` · `openai` | `openai:gpt-5` | resmi | ilgili key |

Varsayılan yol **local**: key yok, ücret yok, veri makineden çıkmaz — ön koşul makinede
`llama-server`'ın ayakta olması. `SONAR_BASE_URL` ile Ollama/LM Studio/gateway'e yönlendirilir.
Chat için ya local model ayakta olmalı ya da bir OpenRouter key'i verilmeli; **abonelik
(Claude/ChatGPT) ile çalışma yolu yok** (sağlayıcı ToS'u, hesap ban riski — [ADR-0002](docs/adr/0002-single-swappable-ai-provider.md)).

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

[Apache-2.0](LICENSE) — permissive + patent koruması.

## Sorumluluk reddi

Sonar bilgi + analiz üretir; **yatırım tavsiyesi değildir**. Karar kullanıcınındır. Emir
iletmez (al-sat yapmaz).
