# Sonar — Milestone Roadmap (v1)

> Tüm sprint/milestone bilgisini tutan ana doküman. Tasarım: `docs/superpowers/specs/`.
> Kararlar: `docs/adr/`. Her milestone'un kendi planı: `docs/superpowers/plans/`.
> Canlı task-içi ilerleme (yürütme sırasında): `.superpowers/sdd/progress.md` (gitignored).

Her milestone **tek başına çalışan/shippable**; kendi planıyla (writing-plans) +
subagent-driven yürütülür. Sıra: plan → subagent-driven execute → final review → merge → sonraki M.

## Durum

| M | Ne ekler (deliverable) | Definition of Done (verify) | ~Task | Durum | Plan |
|---|---|---|---|---|---|
| **M0** | Walking skeleton: tek binary, ticker→fiyat (LLM yok) | `dist/sonar` → tarayıcı → "AAPL" → gerçek fiyat; katmanlar uçtan uca bağlı | 10 | ✅ merged | [m0](superpowers/plans/2026-06-27-m0-walking-skeleton.md) |
| **M1** | Agent omurgası: chat agent + `/api/chat` **SSE** + chat kutusu + MessagePart/registry | "AAPL fiyat" chat'ten gelir; token-token akar; tool-adımı görünür | ~8 | ✅ DoD¹ | `ca55072` |
| **M2** | Deep analiz (UC1) **+ Big Players**: Alpaca fiyat · EDGAR fundamentals/13F/Form4 · FRED makro · teknikler(elle) · news · peers + DeepAnalysis recipe + grafik + `/api/stream/quotes` SSE | **A:** "NVDA" → top-down rapor + Lightweight Chart · **B:** "NVDA'yı kim aldı" → filer + Δ | ~24 | ✅ **merged-ready³** (Faz A+B) | [spec](superpowers/specs/2026-07-13-m2-deep-analysis-and-big-players-design.md) · [plan](superpowers/plans/2026-07-13-m2-deep-analysis-and-big-players.md) · [spike](superpowers/plans/2026-07-13-13f-spike-raporu.md) |
| **M3** | Portföy/Watchlist (UC2/3): aggregate'ler + repo + P&L + paneller | P&L elle = eşleşir; konsantrasyon flag | ~10 | ⏳ planlı | TBD |
| ~~M4~~ | ~~Büyük oyuncular~~ → **M2'ye alındı** (aynı EDGAR altyapısı) | — | — | ↗ M2 | — |
| **M5** | Otonomi (UC4/5): APScheduler + Brief recipe + Alert | sabah brief oluşur; alert cooldown'lı tetikler | ~10 | ⏳ planlı | TBD |
| **M6** | Model katmanı + dağıtım: settings UI (model/endpoint seçimi) · local runtime yönetimi (llama-server indir/spawn, **detect-first**) · CI binary matrix | Settings'ten model seçilir; local tek tıkla ayağa kalkar (ayakta olan endpoint'e dokunulmaz); CI OS-matrix binary üretir | ~10 | ⏳ planlı² | TBD |

**Toplam ≈ 72 task.** Mantık: M0–M1 mimariyi kanıtlar · M2 asıl değeri (derin analiz + büyük oyuncular) ·
M3/M5 genişletir · M6 cilalar+dağıtır.

> ³ **M2, eski M4'ü içine aldı** (2026-07-13): fundamentals (EDGAR companyfacts) ile 13F/Form 4 **aynı**
> altyapıyı (ticker↔CIK + rate-limitli SEC istemcisi) kullanıyor; ayrı milestone tutmak aynı işi iki kez
> yaptırırdı. Tek spec, **iki faz**, arada merge kapısı: **Faz A** derin analiz (tek başına shippable) →
> **Faz B** big players. Faz B **spike ile başlar** (13F toplu veri seti + CUSIP→ticker eşleşme oranı
> ölçülür); geçmezse küratörlü filer evrenine düşer. "Önce ölç, sonra kur" — M6'daki disiplinin aynısı.
> Fiyat kaynağı **Alpaca**'ya geçti (resmî API + WebSocket); key yoksa yfinance fallback + görünür
> kaynak şeridi.

> ¹ **M1 DoD karşılandı** (`ca55072`): `/api/chat` uçtan uca sürüldü → `tool-call` →
> `tool-result` → token-token `text-delta` → `done`. **Güncelleme (2026-07-13):** M1'de yazılan
> Claude Code SDK yolu **söküldü** (abonelik OAuth = ToS/ban riski; SDK = versiyon+fatura riski —
> ADR-0002). Artık **tek loop: LangGraph ReAct**, her sağlayıcı için; model katmanı
> `sonar/agent/model.py` (`SONAR_MODEL`, varsayılan `local:qwen3-14b`). Chat key'siz çalışmaz:
> ya local model ayakta ya OpenRouter key'i. `SONAR_PROVIDER` yok.
> Kalan: kozmetik lint pass (M6 CI'ye kadar bekleyebilir).

> ² **M6 sıralaması bağlayıcı: önce ölç, sonra kur.** Local runtime yönetimi (indirme + spawn +
> Settings) ancak Qwen3 14B Q4 beş-vakalık tool-calling testini **geçerse** yazılır; geçmezse
> varsayılan OpenRouter'a döner ve launcher yazılmaz
> (spec: [model katmanı](superpowers/specs/2026-07-13-model-layer-local-first-design.md)).

> **M1 öncesi review bulguları ✅ çözüldü** (`764bc4b` merged):
> shared-conn → `threading.Lock`; unknown ticker → 404; `@types/react` ^18 pin;
> `sonar.spec` httpx; `test_static` `pytest.skip`. Kozmetik minor'lar (kullanılmayan import,
> type annotation, yfinance yorumu) → M1 CI/lint pass'inde (bekliyor).

> **M1 tasarım notları (`huggingface/tau` referanslı):**
> - Part/event taksonomisi sıfırdan icat edilmez → tau `tau_agent/events` referans; tam liste ADR-0008'de.
> - Chat-persistence şeması **append-only** kurulur (compact ≠ rewrite) → ADR-0004.

## Bağlayıcı kararlar (her milestone bunlara uyar)
- Tool yüzeyi sabit, borsalar plugin (ADR-0001/0005) · derin tool, sayı çekirdekte (ADR-0003)
- Tek model, tek loop; model katmanı env'den sürer, varsayılan local (ADR-0002) · tek SQLite, Redis/vektör yok (ADR-0004)
- LangGraph: chat=ReAct, recipe=StateGraph (ADR-0007) · **Frontend streaming = uniform SSE, AG-UI-ready (ADR-0008)** → M1 chat-SSE, M2 quote-SSE bunu izler

## v2 (v1 sonrası, ayrı roadmap)
UC6 derin büyük-oyuncu gezgini · 13D/13G · screener · push bildirim (Telegram/e-posta) ·
**CopilotKit/AG-UI generative UI** (ADR-0008 omurgası hazır) · TR plugin paketi (`sonar-market-tr`) · backtesting.

## Nasıl güncellenir
Bir milestone bitip merge olunca: bu tablodaki **Durum**'u ✅ yap, **Plan**'a merge edilen plan dosyasını/PR'ı bağla. Yeni milestone planı yazılınca Plan = dosya yolu.
