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
| **M2** | Deep analiz (UC1): ohlcv/technicals(elle)/fundamentals/news/macro/peers + DeepAnalysis recipe + interaktif grafik + `/api/stream/quotes` SSE | "NVDA analiz" → top-down rapor + Lightweight Chart | ~14 | ⏳ planlı | TBD |
| **M3** | Portföy/Watchlist (UC2/3): aggregate'ler + repo + P&L + paneller | P&L elle = eşleşir; konsantrasyon flag | ~10 | ⏳ planlı | TBD |
| **M4** | Büyük oyuncular: EDGAR 13F/Form4 + HoldingsSnapshot/InsiderTrade + Δ | EDGAR/Dataroma ile eşleşir | ~10 | ⏳ planlı | TBD |
| **M5** | Otonomi (UC4/5): APScheduler + Brief recipe + Alert | sabah brief oluşur; alert cooldown'lı tetikler | ~10 | ⏳ planlı | TBD |
| **M6** | AI provider + dağıtım: ChatGPT-OAuth · Claude/MCP server · settings UI · CI binary matrix | her provider çalışır; CI OS-matrix binary üretir | ~10 | ⏳ planlı | TBD |

**Toplam ≈ 72 task.** Mantık: M0–M1 mimariyi kanıtlar · M2 asıl değeri (derin analiz) · M3–M5 genişletir · M6 cilalar+dağıtır.

> ¹ **M1 DoD karşılandı** (`ca55072`): `/api/chat` uçtan uca sürüldü → `tool-call` →
> `tool-result` → token-token `text-delta` → `done`; 31 test yeşil. Varsayılan provider
> **`claude-code`** (abonelik, ADR-0002): API key gerekmez, döngüyü Claude Code SDK sürer
> (ToS istisnası ADR-0007'de). `SONAR_PROVIDER=api-key` → LangGraph ReAct + `SONAR_MODEL`.
> Kalan: kozmetik lint pass (M6 CI'ye kadar bekleyebilir).

> **M1 öncesi review bulguları ✅ çözüldü** (`764bc4b` merged):
> shared-conn → `threading.Lock`; unknown ticker → 404; `@types/react` ^18 pin;
> `sonar.spec` httpx; `test_static` `pytest.skip`. Kozmetik minor'lar (kullanılmayan import,
> type annotation, yfinance yorumu) → M1 CI/lint pass'inde (bekliyor).

> **M1 tasarım notları (`huggingface/tau` referanslı):**
> - Part/event taksonomisi sıfırdan icat edilmez → tau `tau_agent/events` referans; tam liste ADR-0008'de.
> - Chat-persistence şeması **append-only** kurulur (compact ≠ rewrite) → ADR-0004.

## Bağlayıcı kararlar (her milestone bunlara uyar)
- Tool yüzeyi sabit, borsalar plugin (ADR-0001/0005) · derin tool, sayı çekirdekte (ADR-0003)
- Tek swappable AI provider (ADR-0002) · tek SQLite, Redis/vektör yok (ADR-0004)
- LangGraph: chat=ReAct, recipe=StateGraph (ADR-0007) · **Frontend streaming = uniform SSE, AG-UI-ready (ADR-0008)** → M1 chat-SSE, M2 quote-SSE bunu izler

## v2 (v1 sonrası, ayrı roadmap)
UC6 derin büyük-oyuncu gezgini · 13D/13G · screener · push bildirim (Telegram/e-posta) ·
**CopilotKit/AG-UI generative UI** (ADR-0008 omurgası hazır) · TR plugin paketi (`sonar-market-tr`) · backtesting.

## Nasıl güncellenir
Bir milestone bitip merge olunca: bu tablodaki **Durum**'u ✅ yap, **Plan**'a merge edilen plan dosyasını/PR'ı bağla. Yeni milestone planı yazılınca Plan = dosya yolu.
