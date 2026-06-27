# 0001 — Python core + TypeScript UI, monorepo, tek-binary dağıtım

Sonar'ın çekirdeği (agent, tool'lar, veri, analitik) **Python**; UI ayrı bir
**TypeScript/React** frontend. İkisi tek monorepo'da (`backend/` + `frontend/`).
Yayında frontend statik build edilip Python ile birlikte **OS başına tek
kendinden-yeterli binary** (PyInstaller) olarak paketlenir; kullanıcı tek dosya
çalıştırır, tarayıcı açılır.

## Considered Options
- **Full-TS (dexter gibi, Bun):** tek dil/runtime, basit kurulum. **Reddedildi** —
  TS'te yaşamak veriyi paralı/hosted API'ye (ör. Financial Datasets API) bağlamayı
  zorluyor; bu da projenin "bedava / local / bağımsız veri" (yfinance, SEC EDGAR, FRED)
  ve local quant hedefini bozar. Python'ın finans/quant ekosistemi farklılaştırıcı.
- **Python-only web (NiceGUI / Streamlit):** tek dil. **Reddedildi** — hedeflenen
  "app-gibi" deneyim + ileride generative UI (CopilotKit/AG-UI) React/TS dünyasında.

## Consequences
- İki dilli build; frontend build CI'da otomatik (node/bun yalnız build-zamanı, kullanıcıda yok).
- Son kullanıcıda runtime bağımlılığı yok (binary). İkincil dağıtım: `uv tool`/pipx; üçüncül: Docker.
- **Dil ≠ veri-kaynağı.** İleride hosted veri API'si Python tarafında bir Market provider
  olarak eklenebilir — dil değişmeden (bkz. CONTEXT.md: Market).
