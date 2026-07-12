# 0007 — Agent mimarisi: chat=ReAct, yapılandırılmış use-case=deterministik recipe

Üç giriş noktası, use-case'e göre **iki şekil**:

- **Chat (UC7):** LangGraph `create_react_agent` — **dinamik** tool seçimi; `SqliteSaver`
  ile thread memory (aynı SQLite, ADR-0004). **İstisna (ADR-0002):** provider = Claude
  aboneliği ise chat döngüsünü **Claude Code SDK** sürer (ToS; kendi loop'umuzda abonelik
  kullanılamaz) — tool'lar aynı çekirdek, SSE taksonomisi aynı; fark yalnız döngünün kimde
  olduğu. ReAct yolu API-key provider'larında geçerli.
- **DeepAnalysis (UC1) & Brief (UC4):** deterministik **StateGraph** — `gather` node deep
  tool'ları **paralel** çağırır (LLM yok), `synthesize` node **tek** LLM çağrısıyla anlatıyı
  yazar. Sabit reçete (ReAct yok).

**Routing'i UI/scheduler yapar** (entry point = intent); LLM router yok. Dinamik tool
seçimi **yalnız chat'te**.

**Tool katmanı paylaşımlı:** aynı 13 deep tool üç tüketiciye açık — ReAct'e (`@tool`),
recipe'lere (doğrudan Python çağrısı), ve **MCP server**'a (harici beyin yolu: Claude Code
bugün, Codex CLI ileride).

## Considered Options
- **Her şey ReAct:** reddedildi — UC1/UC4'te tool reçetesi sabit; LLM'e keşfettirmek pahalı,
  yavaş, güvenilmez, ADR-0003'e aykırı.
- **Reçeteler düz Python (graf değil):** reddedildi (alt-karar) — web canlı tool-adımı
  streaming + AG-UI hazırlığı için tek-tip LangGraph tercih edildi.
- **`deepagents` harness'ı (LangChain):** reddedildi — asıl değeri context yönetimi
  (auto-compact + büyük tool çıktısını dosyaya offload) ve dinamik planlama/subagent. Bizde
  tool çıktısı hesaplanmış ve küçük (ADR-0003) → overflow tasarımla yok; reçete sabit →
  planlama tool'u boşta. Ayrıca LangChain chat model'i (API key) ister; varsayılan abonelik
  yolunu (Claude Code SDK) süremez → aynı işi yapan ikinci harness bakımı. **Yeniden açma
  koşulu:** api-key provider'larında subagent/planlama paritesi gerçekten istenirse.

## Consequences
- LLM karar yüzeyi minimum → güvenilirlik + düşük token; ADR-0003 ile uyumlu.
- Tek-tip LangGraph `.astream()` → web'de canlı tool-adımı + CopilotKit/AG-UI (v2) hazır.
- Harici beyin (Claude Code / Codex CLI) aynı MCP server'a bağlanır; in-app beyin API key /
  ChatGPT-OAuth ile (ADR-0002).
