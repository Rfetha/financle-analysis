# Next Session — Buradan devam et

> Bir sonraki oturum için handoff. Tam bağlam: `CLAUDE.md` · `docs/ROADMAP.md` · `docs/adr/`.

## Nerede kaldık (2026-07-13)

**M1 DoD kapandı. Provider mimarisi yeniden kuruldu: tek loop + local-first. PUSH'SUZ.**

- `master` origin'in **7+ commit önünde** (push kimlik sorunu: repo `Rfetha/...`, gh `RfethaEgeist`
  ile giriş yapmış → `gh auth login` ile kişisel hesaba geçmek gerek).
- **31 test yeşil.**

### Mimari değişiklik (2026-07-13) — spec + ADR'ler güncel
Claude Code SDK yolu **söküldü**. Gerekçe (ADR-0002'de tam metin): abonelik OAuth'u üçüncü-parti
üründe yasak (Anthropic ToS, Şubat 2026 → Nisan'da uygulandı; ihlal = **kullanıcının** hesabı banlanır);
ToS-uyumlu tek yol olan SDK ise uygulamayı dış bir binary'nin davranışına (versiyon kayması) ve
sağlayıcının fatura politikasına bağlıyordu.

**Yeni şekil:**
- **Tek loop:** chat = LangGraph ReAct, provider ne olursa olsun (ADR-0007).
- **Model katmanı** (`sonar/agent/model.py`): `SONAR_MODEL="<provider>:<model>"`
  - `local:qwen3-14b` (**varsayılan**) → llama-server `http://localhost:8080/v1`, key yok
  - `openrouter:<model>` → `OPENROUTER_API_KEY`
  - `anthropic:` / `openai:` → ilgili key
  - `SONAR_BASE_URL` ile Ollama/LM Studio/gateway'e yönlenir. Local ve OpenRouter aynı
    OpenAI-uyumlu istemciden geçer (fark: `base_url`).
- **Katman sınırı testli:** `tests/test_layering.py` — `api/ tools/ domain/ store/ market/` içinde
  provider ithali (langchain/langgraph/openai/anthropic) yasak.
- **Non-goal oldu:** MCP "harici beyin" kapısı · deepagents · finansa-FT beyin modeli.

Spec: `docs/superpowers/specs/2026-07-13-model-layer-and-mcp-door-design.md`

### Local model: ÖLÇÜLDÜ ve KİLİTLENDİ (2026-07-13)
Qwen3 14B Q4 tool-calling kabul testi **5/5 geçti** → local varsayılan kesin. Motor **llama.cpp** (kilit).
Kilit komut (ölçülmüş: 43.8 tok/s, 16k context, VRAM 10.6/12.2):
```powershell
cd C:\tools\llama
.\llama-server.exe -m models\Qwen3-14B-Q4_K_M.gguf --jinja -fa on -c 16384 -ctk q8_0 -ctv q8_0 -ngl 99 --port 8080
```
Spekülatif decoding ölçüldü → kazanç yok, alınmadı. KV quant (q8_0) alındı → hız aynı, 2× context.
Server ayakta değilse chat, komutu içeren açık `error` event'i döner (`model.explain`).

## Hemen sıradaki iş (sen seç)

- **M2 (Deep analiz)** — asıl değer. ROADMAP M2. Reçeteler döngü kullanmaz → provider'dan bağımsız;
  sentez adımı için model katmanına `synthesize` portu doğacak.
- **Managed launcher** (M6'dan öne çekilebilir) — GGUF indirme + llama-server spawn + Settings ekranı;
  **detect-first**: endpoint'te sunucu varsa Sonar süreç başlatmaz (kullanıcının Ollama/LM Studio'suna
  dokunmaz). Az bilen kullanıcı için "tek tık".
- **UI design pass** — `impeccable:frontend-design`, TradingView-vari (memory: `ui-design-direction`).
- **Push** — `master` → origin; kimlik düzeltmesi gerekiyor (repo `Rfetha/...`, gh `RfethaEgeist`).

## Bilinen açıklar / notlar
- **Chat artık key'siz çalışmıyor**: ya llama-server ayakta olacak ya OpenRouter key'i verilecek.
  (Bilinçli bedel — ADR-0002.)
- Chat-persistence tek-oturum (`MemorySaver`). Kalıcılık → `SqliteSaver` (aynı DB, ADR-0004).
- `dist/sonar.exe` eski (M0 build). Kozmetik lint pass yapılmadı.

## Çalıştırma / test
```bash
cd backend && uv run pytest          # 31 passed
cd backend && uv run pytest -m slow  # gerçek yfinance
cd backend && uv run sonar           # uygulama (local model ya da OPENROUTER_API_KEY gerekir)
cd frontend && npm run dev           # 2-process dev (/api → :8000 proxy)
```

## Açık karar yok
Sıra: local ölçümü → (launcher ya da bulut varsayılanı) → push → UI pass → M2.
