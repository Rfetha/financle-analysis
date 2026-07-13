# Sonar — Mimari (as-built)

> Bugün **kodda ne varsa** o. Kararların *gerekçesi* ADR'lerde, *planı* spec'lerde; burası harita.
> Alan dili: [`CONTEXT.md`](../CONTEXT.md) · Kararlar: [`docs/adr/`](adr/) · Yol haritası: [`ROADMAP.md`](ROADMAP.md)
> Son güncelleme: 2026-07-13 (M1 tamam, M2 öncesi)

## Bir bakışta

Sonar **local-first** bir masaüstü uygulamasıdır: beyin (LLM) kullanıcının kendi makinesinde koşar,
veri dışarı çıkmaz, API key gerekmez. Local koşamayan/istemeyen için kaçış kapısı: API key (OpenRouter
· Anthropic · OpenAI). Tek binary (PyInstaller) → tarayıcı açar; backend statik frontend'i servis eder.

```
tarayıcı (React SPA)
   │  POST /api/chat            SSE: text-delta · tool-call · tool-result · error · done
   ▼
api/            FastAPI — HTTP + SSE çerçeveleme. Provider bilmez.
   ▼
agent/          LangGraph ReAct döngüsü (chat) · model katmanı · tool sarmalayıcıları · event map
   │                        │
   │                        └── model/  env → chat model:  local(llama.cpp) | openrouter | anthropic | openai
   ▼
tools/          Deep tool'lar — hesaplanmış, yapılandırılmış sonuç döner (LLM aritmetik yapmaz)
   ▼
market/         Market plugin = Anti-Corruption Layer (US: yfinance/EDGAR/FRED) → domain VO
   ▼
domain/  store/ Value Object'ler + aggregate'ler · tek SQLite (DB + TTL cache + history + FTS5)
```

## Katmanlar ve bağımlılık kuralı

| dizin | sorumluluk | bilmediği şey |
|---|---|---|
| `api/` | HTTP, SSE çerçeveleri, statik dosyalar | hangi model/provider, LangGraph |
| `agent/` | ReAct döngüsü, model katmanı, tool sarmalama, LC event → Sonar event | domain kuralları |
| `tools/` | deep tool'lar (hesap burada, ADR-0003) | LLM, provider |
| `market/` | dış kaynak → domain VO çevirisi (ACL) | LLM, HTTP katmanı |
| `domain/` | Symbol · Money · Quote … (frozen VO'lar) | her şey (saf) |
| `store/` | SQLite: DB · TTL cache · (ileride) history/FTS5 | LLM, HTTP |

**Sert kural:** `api/ tools/ domain/ store/ market/` içinde **provider kütüphanesi ithal edilemez**
(`langchain*`, `langgraph`, `openai`, `anthropic`). Bu bir niyet değil, **test**:
`backend/tests/test_layering.py` import'ları tarar; sızıntı kırmızıya düşer.

## Chat akışı (M1, çalışan)

1. `POST /api/chat {message, thread_id}` → `api/app.py`
2. `agent/graph.py::make_streamer` → LangGraph `create_react_agent` (ilk istekte lazy kurulur;
   model katmanı env'den seçer, hata olursa tek `error` event'ine düşer)
3. Model tool çağırmaya karar verir → `agent/tools.py` → `tools/quote.py` → `market/us.py` → cache/yfinance
4. `agent/events.py::map_lc_event` LangChain `astream_events(v2)` akışını **Sonar taksonomisine** çevirir:
   `text-delta` · `tool-call` · `tool-result` · `error` · `done` (ADR-0008)
5. Frontend part-type → component registry ile çizer (AG-UI'a rewrite'sız geçiş için)

Loglama: her istekte tool çağrısı/sonucu, hata ve süre `loguru` ile görünür.

## Model katmanı (`agent/model.py`)

`SONAR_MODEL="<provider>:<model>"` — varsayılan `local:qwen3-14b`.

| provider | endpoint | key |
|---|---|---|
| `local` **(varsayılan)** | `http://localhost:8080/v1` — llama.cpp / llama-server | yok |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `anthropic` · `openai` | resmi | ilgili key |

`local` ve `openrouter` **aynı** OpenAI-uyumlu istemciden geçer; tek fark `base_url`. `SONAR_BASE_URL`
ile Ollama / LM Studio / gateway'e yönlenir. Sağlayıcıdan **tool-calling zorunlu** yetenek.
Local server kapalıysa `model.explain()` çalıştırma komutunu içeren açık bir hata döndürür
(sessiz buluta kaçış yok).

**Kilit local yapılandırma** (ölçüldü: 43.8 tok/s, 16k context, VRAM 10.6/12.2 — RTX 5070):
```bash
llama-server -m Qwen3-14B-Q4_K_M.gguf --jinja -fa on -c 16384 -ctk q8_0 -ctv q8_0 -ngl 99 --port 8080
```

## Değişmezler (bunlar bozulursa mimari bozulur)

1. **Tool derin, LLM sığ** (ADR-0003): sayı `tools/` + `analytics` içinde hesaplanır; LLM yalnız sentezler.
2. **Tool yüzeyi sabit, borsalar plugin** (ADR-0001/0005): market veremediği yeteneğe `Unsupported` döner.
3. **Tek loop** (ADR-0002/0007): provider ne olursa olsun döngü LangGraph'ta. Chat = ReAct (dinamik);
   DeepAnalysis/Brief = deterministik StateGraph (sabit reçete — M2'de gelir).
4. **Tek SQLite** (ADR-0004): DB + TTL cache + history + FTS5, WAL. Redis/vector DB yok.
5. **Uniform SSE** (ADR-0008): yeni yetenek = yeni event tipi; taksonomi genişler, yeniden yazılmaz.
6. **Katman sınırı testli** (yukarıda).

## Bilinçli olmayanlar (non-goal)

Broker/emir · çoklu kullanıcı/auth/SaaS · abonelik (Claude/ChatGPT) ile çalışma — sağlayıcı ToS'u,
hesap ban riski (ADR-0002) · Claude Code / Agent SDK · MCP server ("harici beyin" kapısı) ·
`deepagents` harness'ı · finansa fine-tune edilmiş beyin modeli · TR piyasaları (v1) · SSR.

## Nerede ne yazıyor

| soru | dosya |
|---|---|
| Alan dili (Position, Filer, Deep Analysis…) | [`CONTEXT.md`](../CONTEXT.md) |
| Aggregate / VO sınırları | [`specs/2026-06-27-domain-model.md`](superpowers/specs/2026-06-27-domain-model.md) |
| Neden bu provider/motor? | [`adr/0002`](adr/0002-single-swappable-ai-provider.md) · [`specs/2026-07-13-model-layer-local-first-design.md`](superpowers/specs/2026-07-13-model-layer-local-first-design.md) |
| Neden ReAct + StateGraph? | [`adr/0007`](adr/0007-agent-architecture.md) |
| Neden tek SQLite? | [`adr/0004`](adr/0004-single-sqlite-store-no-redis-no-vectordb.md) |
| Neden SSE, AG-UI'sız? | [`adr/0008`](adr/0008-frontend-streaming-architecture.md) |
| Sıradaki iş | [`ROADMAP.md`](ROADMAP.md) · [`NEXT_SESSION.md`](../NEXT_SESSION.md) |
