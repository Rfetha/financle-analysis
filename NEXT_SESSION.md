# Next Session — Buradan devam et

> Bir sonraki oturum için handoff. Tam bağlam: `CLAUDE.md` · `docs/ROADMAP.md` · `docs/adr/` ·
> `docs/ARCHITECTURE.md`. Canlı task ilerlemesi: `.superpowers/sdd/progress.md` (gitignored).

## Nerede kaldık (2026-07-15)

**M2 TAMAMLANDI — Faz A (Deep Analysis) + Faz B (Big Players). PUSH'LANDI, master'a MERGE EDİLMEDİ.**

- Branch: `feat/m2-deep-analysis-big-players` — **48 commit**, origin'e push'lu (`Rfetha` hesabıyla; gh
  aktif hesabı `Rfetha` olmalı — `RfethaEgeist` yazamıyor: `gh auth status` → değilse `gh auth login`).
- **136 test yeşil** · slow **6 passed / 2 skipped** (Alpaca, `.env` izolasyonu) · frontend build+tsc temiz.
- **Gerçek SEC verisiyle kanıtlandı:** 2 çeyrek 13F ingest → NVDA holders + Δ (5796 filer, 411 yeni /
  290 çıkış, opsiyon ayrı). Parse→CUSIP→amendment→Δ tümü canlı veride çalıştı.

### Ne eklendi (M2)
- **Faz A:** Alpaca fiyat (Strategy, key yoksa yfinance) · EDGAR fundamentals+peers · FRED makro ·
  elle teknikler (RSI/MACD/BB/… numpy) · RSS haber · DeepAnalysis recipe (paralel gather + tek LLM
  synthesize) · `/api/analyze` · `/api/ohlcv` · `/api/stream/quotes` (+Alpaca WS) · Lightweight Charts +
  analiz görünümü (ilerleme rayı + "yazıyor").
- **Faz B:** 13F ingestion (amendment RESTATEMENT/NEW HOLDINGS + prune + özet trend) · Δ sınıflaması ·
  Form 4 insider + cluster · FINRA short · arka plan ingest (startup lifespan + `/api/ingest/status`) ·
  CusipMap (isim-eşleşmeli) · get_institutional_holders/filer_holdings · recipe **BÜYÜK OYUNCULAR** node ·
  ReAct'e 10 tool · frontend big-players chip + ingest şeridi.

### B0 spike kararı (gerçek veri)
13F: 3.8M satır/çeyrek. CUSIP→ticker naive isim-eşleşmesi %56 AMA `NAMEOFISSUER` her satırda → gösterim
CUSIP'e takılmaz → **bulk index** (curated değil). FIGI %12 (elendi). Ticker-çözülür satırlara filtre.
Rapor: `docs/superpowers/plans/2026-07-13-13f-spike-raporu.md`.

## Hemen sıradaki iş (sen seç)

1. **Faz B final whole-branch review** — Faz A'da yapıldı (0 Critical, 4 Important düzeltildi); Faz B için
   HENÜZ yapılmadı. Merge öncesi önerilir. (`superpowers:requesting-code-review`, en güçlü model.)
2. **master'a merge** — review sonrası. `superpowers:finishing-a-development-branch`.
3. **TAM M2 demosu** — aşağıdaki "Çalıştırma"; llama-server + app + 13F ingest → "NVDA" → Büyük Oyuncular.
4. **UI design pass** — analiz görünümü + genel TradingView-vari cila (`impeccable:frontend-design`);
   memory: `ui-design-direction`. Kullanıcı UX'i "tam OK değil, sonra" dedi.
5. **M3** (Portföy/Watchlist) ya da **M6** (Settings UI — `.env`'i UI'dan yönet: model/Alpaca key).

## Bilinen açıklar / deferred (loglu, düşük risk)
- **big_players alt-parça izolasyonu:** recipe'de holders+insiders+short tek lambda; insiders/short
  patlarsa holders da kaybolur (rapor çökmez — `_run` yakalar). Her alt-parçayı ayrı sarmala.
- **Alpaca canlı WS:** parser unit-test'li; canlı connect yolu suite'te skip (test `.env` izolasyonu) ve
  mevcut UI'a bağlı değil (polling çalışır). Gerçek WS bir bug taşıyor olabilir — açık test-key'iyle bak.
- **peers cold-scan ~20s** (gerçek EDGAR; tool 24s cache'ler) → hızlı yol Faz B SIC tablosuyla (ileride).
- **Faz A final-review minor'ları:** MACD `_need` sınırı, RSI 0/0→100, dxy=Broad Dollar etiketi,
  fresh-model-per-request, unencoded ticker (Yahoo URL). `.superpowers/sdd/review-FAZA-final-report.md`.

## Çalıştırma / test / TAM demo
```bash
cd backend && uv run pytest              # 136 passed
cd backend && uv run pytest -m slow      # gerçek EDGAR/FRED/yfinance/Form4 (Alpaca key varsa +2)

# TAM M2 demosu:
# 1) ayrı terminalde llama-server (kilit komut ADR/ARCHITECTURE'da):
#    llama-server -m Qwen3-14B-Q4_K_M.gguf --jinja -fa on -c 16384 -ctk q8_0 -ctv q8_0 -ngl 99 --port 8080
# 2) .env'e (opsiyonel) SONAR_ALPACA_KEY/SECRET — yoksa yfinance fallback + sarı şerit
cd backend && uv run sonar               # startup'ta 13F otomatik iner (~2 dk); /api/ingest/status
cd frontend && npm run dev               # 2-process dev (/api → :8000)
# tarayıcı → Derin Analiz → "NVDA" → rapor + BÜYÜK OYUNCULAR (13F Δ + insider cluster + short)
```

## Env / config
- Kod sabitleri: `backend/sonar/config.py` (TTL'ler + `.env` loader). Kullanıcı key'leri: `.env`
  (gitignored; şablon `.env.example`). `SONAR_SKIP_INGEST=1` 13F ingest'i kapatır (test/CI).
- Model: `SONAR_MODEL` (varsayılan `local:qwen3-14b`). Fiyat: `SONAR_ALPACA_KEY/SECRET`.
  EDGAR nezaketi: `SONAR_CONTACT`.

## Açık karar yok
Sıra: (Faz B review) → merge → (UI pass ya da M3/M6).
