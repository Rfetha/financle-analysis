# Next Session — Buradan devam et

> Bir sonraki oturum için handoff. Tam bağlam: `CLAUDE.md` · `docs/ROADMAP.md` · `docs/adr/`.

## Nerede kaldık (2026-07-12)

**M1 (Agent omurgası) DoD kapandı — abonelik yolu canlı doğrulandı. PUSH'SUZ.**

- `master` origin'in **4 commit önünde** (M1 + Claude Code SDK provider yolu).
- **31 test yeşil**. Canlı akış: "AAPL fiyatı ne?" → `tool-call` → `tool-result` → `text-delta`
  (API key kullanılmadan, lokal Claude Code auth'u ile).

### M1'de ne var
- **İki provider yolu, tek arayüz** (`make_streamer(registry, cache, ttl) -> (message, thread_id)
  -> SSE event akışı`), `SONAR_PROVIDER` ile seçilir:
  - `claude-code` (**varsayılan**, ADR-0002 abonelik önceliği): döngüyü Claude Code SDK sürer
    (ToS gereği — kendi loop'umuzda abonelik kullanılamaz). Quote tool = in-process SDK MCP tool;
    dahili Read/Bash/Edit kapalı, `setting_sources=[]` (repo ayarları sızmaz). `sonar/agent/claude_code.py`.
  - `api-key`: LangGraph `create_react_agent` (ReAct) + `SONAR_MODEL` (`sonar/agent/graph.py`).
- `sonar/agent/events.py`: tek SSE taksonomisi (text-delta/tool-call/tool-result/error/done, ADR-0008);
  iki kaynak (`map_lc_event` · `map_sdk_message`) aynı event'lere düşer → frontend registry değişmedi.
- `api/app.py`: `POST /api/chat` → SSE; auth/provider/tool hatası → tek `error` event.
- `frontend/chat.tsx`: fetch+ReadableStream SSE parser · part-type→component registry · koyu minimal UI.

## Hemen sıradaki iş (bu sırayla)

1. **Push** — `master` → origin.
2. **UI design pass** — `impeccable:frontend-design`, yön = **TradingView-vari** (koyu/modern/data-dense;
   memory: `ui-design-direction`). M1 UI şu an işlevsel-ama-minimal; tasarım sistemi + v1 wireframe'ler.
3. **M2 (Deep analiz)** — `writing-plans` → `subagent-driven-development`. Bkz ROADMAP M2.

## Bilinen açıklar / notlar
- **Kozmetik lint pass** M1'de yapılmadı (kullanılmayan import vб.) → CI/lint kurulunca temizlenir.
- `dist/sonar.exe` eski (M0 500-bug'lı build). Ayrıca **abonelik yolu Claude Code CLI'ının kurulu
  olmasını gerektirir** (SDK onu subprocess olarak sürer) → tek-binary paketlemede ya CLI şartı
  yazılır ya da o build `SONAR_PROVIDER=api-key` ile gider. M6 (settings UI) kararı.
- Chat-persistence tek-oturum: ReAct yolunda `MemorySaver`, SDK yolunda process-içi
  `thread_id -> session_id` dict. Kalıcılık → `SqliteSaver` / SDK `session_store` (aynı DB, ADR-0004).

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
