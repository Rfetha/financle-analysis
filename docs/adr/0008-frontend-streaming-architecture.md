# 0008 — Frontend streaming mimarisi: uniform SSE backbone, AG-UI-hazır

Agent ve canlı veri **SSE** ile akar — tek tip event-stream omurgası (LangGraph
`.astream()` → FastAPI SSE → React); yavaş/statik veri req/resp + cache. Mesajlar tipli
"part" listesi + part-type→component registry; SSE event tipleri AG-UI ile hizalı → v2
CopilotKit/AG-UI geçişi **rewrite değil map**. **Vite+React+TS, SSR YOK** (SSE/streaming/
AG-UI'ın hiçbiri SSR gerektirmez — SSR yalnız ileride SEO'lu hosted SaaS senaryosu için).

## Kanallar
**SSE (canlı):**
- `/api/chat` — agent token akışı + tool-adımı/araç-kartı event'leri (M1). AG-UI omurgası.
- `/api/stream/quotes?symbols=...` — açık chart/panel için canlı son-fiyat/son-bar push (M2).
  **Baştan SSE (uniform), polling değil** — sonradan migrasyon derdi olmasın.

**Req/resp + cache (statik/yavaş):** OHLCV geçmiş barlar, fundamentals, 13F/insider, peers,
macro snapshot, deep-analysis raporu, portföy/watchlist CRUD.

> Gerekçe: tek streaming mekanizması (SSE) hem chat hem canlı-quote için → uniform omurga,
> AG-UI geçişi ucuz. Çeyreklik/yavaş veriyi stream etmek anlamsız → req/resp+cache.

## Reconnect / backoff
- **Chat:** `fetch` + `ReadableStream` (EventSource değil — header/abort kontrolü; yarım
  üretimi **sessiz resume etmez**). Kopunca → hata mesajı + retry butonu.
- **Live-quote SSE:** native `EventSource` auto-reconnect + exponential backoff
  (1→2→4…cap 30s); sekme gizli / piyasa kapalı → duraklat; server ~15s heartbeat ping.

## Mesaj-bileşeni soyutlaması (AG-UI'a rewrite'sız geçiş)
- Asistan turu = tipli **part** listesi: `text` (token-append) · `tool_call` (araç-kartı:
  ad+arg+status) · `tool_result` · (v2) `component` (agent'ın seçtiği UI widget = generative
  UI kancası).
- `<MessagePart>` renderer → **part-type → React component registry** (M1: text/tool_call/
  tool_result; v2: agent-driven `component` tipleri eklenir).
- SSE event tipleri AG-UI'ın event tipleriyle (text-delta, tool-call-start/args/end…) hizalı.
- **Part/event taksonomisini sıfırdan icat etme:** referans = `huggingface/tau`
  (`tau_agent/events`) — çalışan bir agent-stream sözleşmesi. Oradan taşınacak set:
  `text-delta` · `tool-call` · `tool-result` · `reasoning` · `error` · `usage/context`
  (token/bağlam muhasebesi). Sonar-özel ek: M2'de `quote-tick` · `chart`. Taksonomi M1'de
  bu tam listeyle kurulur ki M2 quote-SSE **genişletme** olsun, yeniden yazma değil.

## Consequences
- **M0 etkilenmez** (chat M1, quote-stream M2; M0 quote tek-seferlik fetch). M0 minimal kalır.
- M1 plan'ı `/api/chat` SSE + MessagePart/registry'yi bu ADR'ye göre kurar.
- M2 plan'ı `/api/stream/quotes` SSE kanalını (polling değil) kurar.
- v2'de CopilotKit/AG-UI = event-tip map'leme; mesaj-bileşeni mimarisi yeniden yazılmaz.
