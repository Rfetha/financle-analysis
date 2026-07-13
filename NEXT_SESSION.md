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

## Hemen sıradaki iş (bu sırayla)

1. **Local tool-calling ölçümü (bağlayıcı karar noktası)** — llama-server + Qwen3 14B Q4 ile 5 vaka:
   tek ticker · çoklu ticker · bilinmeyen sembol · kapsam dışı (PE) · sohbet (tool çağırmamalı).
   ```powershell
   cd C:\tools\llama
   .\llama-server.exe -m models\Qwen3-14B-Q4_K_M.gguf --jinja -c 16384 -ngl 99 --port 8080
   ```
   **Geçerse** local varsayılan kalır → managed launcher yazılır (GGUF indirme + spawn + Settings;
   detect-first: endpoint'te sunucu varsa Sonar süreç başlatmaz). **Geçmezse** önce llama.cpp grammar
   zorlaması, o da yetmezse varsayılan OpenRouter'a döner (ADR-0002 bu tetiği yazıyor).
2. **Push** — `master` → origin (kimlik düzeltildikten sonra).
3. **UI design pass** — `impeccable:frontend-design`, yön = TradingView-vari (memory: `ui-design-direction`).
4. **M2 (Deep analiz)** — Bkz ROADMAP M2. Reçeteler döngü kullanmaz → provider'dan bağımsız.

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
