# Next Session — Buradan devam et

> Bir sonraki oturum için handoff. Tam bağlam: `CLAUDE.md` · `docs/ROADMAP.md` · `docs/adr/`.

## Nerede kaldık (2026-07-06)

**M1 (Agent omurgası) kodu master'da — henüz PUSH'SUZ.** M0 + pre-M1 fix'ler merged.

- `master` origin'in **3 commit önünde**: `71c43c1` (pre-M1 fix) · `764bc4b` (merge) · `17fd126` (M1).
- **25 test yeşil** (tool wiring + SSE event map deterministik). `tsc` temiz, frontend build OK.
- Pre-M1 review bulguları (M0 final) ✅ çözüldü: shared-conn `threading.Lock`, unknown ticker 404,
  `@types/react` ^18 pin, `sonar.spec` httpx, `test_static` skip.

### M1'de ne var
- `sonar/agent/`: LangGraph `create_react_agent` (ReAct) · quote tool `@tool` · `init_chat_model`
  env-driven provider (ADR-0002 API-key) · `MemorySaver` thread memory.
- `sonar/agent/events.py`: SSE taksonomisi (text-delta/tool-call/tool-result/error/done, tau-hizalı,
  ADR-0008) + `astream_events(v2)` → Sonar event map'i.
- `api/app.py`: `POST /api/chat` → `StreamingResponse` (SSE); key/provider hatası → tek `error` event.
- `frontend/chat.tsx`: fetch+ReadableStream SSE parser · part-type→component registry · koyu minimal UI.

## Hemen sıradaki iş (bu sırayla)

1. **M1 canlı doğrulama (DoD kapanışı)** — gerçek key ile token akışı + tool-adımı görünürlüğü:
   ```powershell
   $env:ANTHROPIC_API_KEY="sk-..."   # opsiyonel: $env:SONAR_MODEL="anthropic:claude-sonnet-5"
   cd backend; uv run sonar          # tarayıcı → "AAPL fiyatı ne?" → token-token akış + araç-kartı
   ```
   ⚠️ Default model id `anthropic:claude-sonnet-5`; API kabul etmezse `SONAR_MODEL` ile override.
2. **Push** — `master` → origin (doğrulama sonrası).
3. **UI design pass** — `impeccable:frontend-design`, yön = **TradingView-vari** (koyu/modern/data-dense;
   memory: `ui-design-direction`). M1 UI şu an işlevsel-ama-minimal; tasarım sistemi + v1 wireframe'ler.
4. **M2 (Deep analiz)** — `writing-plans` → `subagent-driven-development`. Bkz ROADMAP M2.

## Bilinen açıklar / notlar
- **Kozmetik lint pass** M1'de yapılmadı (kullanılmayan import vб.) → CI/lint kurulunca temizlenir.
- `dist/sonar.exe` eski (M0 500-bug'lı build) — fix'li binary için yeniden build (`sonar.spec` httpx eklendi).
- Chat-persistence şu an `MemorySaver` (tek-oturum). Restart'lar arası kalıcılık → `SqliteSaver`
  (aynı DB, ADR-0004 append-only) yükseltme yolu `graph.py`'de not düşülü.

## Çalıştırma / test / build
```bash
cd backend && uv run pytest          # 25 passed
cd backend && uv run pytest -m slow  # gerçek yfinance
cd backend && uv run sonar           # uygulama (chat için API key gerekir)
cd frontend && npm run dev           # 2-process dev (/api → :8000 proxy)
```

## Branch durumu
- `master` = ana hat (M0 + pre-M1 fix + M1), **push bekliyor**.
- `fix/pre-m1-review`, `m0-walking-skeleton`, `fix/quote-robustness-and-license` = merged, silinebilir.

## Açık karar yok
LICENSE Apache-2.0 · UI yönü TradingView-vari · M1 kod tamam. Sıra: canlı doğrulama → push → UI pass → M2.
