# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje

**Sonar** — OSS, provider-bağımsız, otonom çalışabilen bir **ABD borsası** araştırma
asistanı. Portföy + watchlist izler, tek hisseyi (makro + mikro + teknik + "büyük
oyuncular" + haber) derinlemesine araştırır, sabah otonom brief üretir.

**Durum:** geliştirme erken fazda. Aktif milestone takibi → `docs/ROADMAP.md`.
Yürütme sırasında canlı task ilerlemesi → `.superpowers/sdd/progress.md` (gitignored).

## Repo yapısı (monorepo)

```
backend/          Python paketi (FastAPI + LangGraph + tools + store), uv ile yönetilir
  sonar/          domain/ · store/ · market/ · tools/ · api/ · cli.py
  tests/          pytest
frontend/         Vite + React + TypeScript SPA (yayında statik build → backend servis eder)
docs/             ROADMAP.md · adr/ · superpowers/specs/ · superpowers/plans/
CONTEXT.md        ubiquitous language sözlüğü (domain terimleri — koda birebir yansır)
```

## Komutlar

```bash
# Backend (cd backend)
uv sync                         # .venv + bağımlılıklar (uv kullanıyoruz, pip değil)
uv run pytest                   # testler (slow/ağ testleri varsayılan dışlanır)
uv run pytest -m slow           # gerçek dış-API (yfinance) testleri
uv run sonar                    # uygulamayı çalıştır (uvicorn + tarayıcı açar)

# Frontend (cd frontend)
npm install
npm run dev                     # Vite dev server (/api → :8000 proxy) — backend ayrı çalışırken
npm run build                   # dist/ üretir

# Tek-binary (repo kökü, statik build paket içine kopyalandıktan sonra)
uv run pyinstaller sonar.spec --noconfirm     # dist/sonar(.exe)
```

## Bağlayıcı kararlar (ADR'ler — bozma; değişiklik gerekirse ADR + spec güncelle)

- **Tool yüzeyi sabit, borsalar plugin** (ADR-0001/0005). 13 tool'luk sözleşme değişmez;
  her market (US v1) doldurur, veremediği yeteneğe `Unsupported` döner. Portföy/watchlist/
  alert/brief market'ten bağımsız (çekirdek).
- **Derin tool** (ADR-0003): tool hesaplanmış/yapılandırılmış sonuç döner; LLM aritmetik
  yapmaz, yalnız sentezler. Sayı işi `analytics` çekirdeğinde.
- **Tek SQLite** (ADR-0004): DB + TTL cache + history + FTS5, WAL açık. Redis yok, vector
  DB yok (gerekirse `sqlite-vec`).
- **Agent = LangGraph** (ADR-0006/0007): chat = `create_react_agent` (ReAct, dinamik tool);
  DeepAnalysis/Brief = deterministik StateGraph (sabit reçete, LLM yalnız synthesize node).
- **Tek swappable AI provider** (ADR-0002): ChatGPT/Codex-OAuth · Claude (Claude Code/MCP
  üzerinden, ToS) · API key. Aynı anda tek provider, kullanıcı seçer. Local sonra.
- **Frontend uniform SSE** (ADR-0008): chat + canlı-quote SSE ile akar; mesaj = tipli
  "part" listesi + component registry → AG-UI'a rewrite'sız geçiş. **SSR yok.**
- **US-first.** TR (BIST/TEFAS) v1'de yok → ileride ayrı paket `sonar-market-tr`.
- **Non-goal:** broker/emir YOK (sadece analiz/izleme). Çoklu kullanıcı/auth/SaaS yok.
  Opsiyon akışı/dark pool yok (ücretli).

## Stack

Python · FastAPI · LangGraph(+LangChain) · raw `sqlite3` · httpx · yfinance · SEC EDGAR ·
FRED · feedparser · APScheduler · uv · PyInstaller · Vite+React+TS · Lightweight Charts.
Teknik göstergeler **elle yazılır** (numpy/pandas, ADR-0006) — TA-Lib/pandas-ta yok.

## Doküman haritası
- Vizyon/use-case: `docs/superpowers/specs/2026-06-27-financle-us-equity-agent-design.md`
- Domain (aggregate/VO): `docs/superpowers/specs/2026-06-27-domain-model.md`
- Kararlar: `docs/adr/0001..0008`
- Milestone: `docs/ROADMAP.md` · Milestone planları: `docs/superpowers/plans/`
- Katkı/dev: `CONTRIBUTING.md`

## Metodoloji
Global `~/.claude/CLAUDE.md` (Universal Coding Methodology) geçerli: YAGNI, surgical
changes, deep modules. Domain dili = `CONTEXT.md` (kod birebir bu isimleri kullanır).
