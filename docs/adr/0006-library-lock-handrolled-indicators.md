# 0006 — Kütüphane kilidi; teknik göstergeler elle yazılır

## Locked stack
- **Backend:** FastAPI · **Agent:** LangGraph (+ LangChain) — tek loop, ReAct/StateGraph (ADR-0007)
- **Model:** model katmanı `sonar/agent/model.py` (ADR-0002) — OpenAI-uyumlu tek istemci
  (`langchain-openai`; local + OpenRouter aynı yoldan) + doğrudan sağlayıcılar için
  `init_chat_model` (langchain-anthropic …). Varsayılan `local` (llama-server).
  MCP adapter'ı (`langchain-mcp-adapters`) **düştü** (2026-07-13): MCP "harici beyin" kapısı non-goal.
- **Store:** raw `sqlite3` (ORM yok) · **HTTP:** httpx
- **Veri:** yfinance · SEC EDGAR (raw httpx) · FRED (raw httpx) · feedparser (RSS)
- **Scheduler:** APScheduler · **Paketleme:** uv + PyInstaller
- **Frontend:** Vite + React · **Grafik:** TradingView Lightweight Charts (+ matplotlib backend PNG, statik artefakt için)

## Teknik göstergeler: **elle yazılır** (numpy/pandas, `analytics` modülü)

### Considered Options
- **pandas-ta:** bakım **inaktif**, ~2026-07-01'de arşivlenebilir. Fork `pandas-ta-classic`
  var ama numba dep + 150 gösterge → ~8 göstergelik v1 için aşırı.
- **TA-Lib:** C kütüphanesi; binary wheel'lerle kurulabilir ama PyInstaller `--hidden-import`
  zahmeti + ağır bundle → tek-binary sözüyle sürtüşür; ~8 gösterge için aşırı.
- **Elle yazmak (seçildi):** RSI(Wilder) / MACD / BB / EMA / SMA / ATR / volume-spike /
  destek-direnç ~8 küçük fonksiyon; sıfır ekstra dep, temiz bundle, tam kontrol.

### Consequences
- v1 göstergeleri bizim → doğruluk **referans-değer unit testleriyle** garanti.
- Gösterge sayısı patlarsa (50+ / candlestick pattern) → o zaman pandas-ta-classic/TA-Lib. Şimdi değil.
- ADR-0003 (analytics çekirdekte, deterministik) ile birebir.
