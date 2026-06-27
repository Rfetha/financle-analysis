# Katkı Rehberi (Contributing)

## Önkoşullar
- **uv** (Python paket/env yöneticisi) — https://docs.astral.sh/uv/  ·  Python ≥ 3.12
- **Node ≥ 20 + npm** (frontend build için; son kullanıcıda gerekmez)

## Kurulum
```bash
git clone <repo> && cd sonar
cd backend && uv sync          # .venv + bağımlılıklar (pip/aktivasyon yok — uv run kullan)
cd ../frontend && npm install
```

## Geliştirme

**Testler:**
```bash
cd backend
uv run pytest                  # birim testler (slow/ağ dışlanır)
uv run pytest -m slow          # gerçek dış-API (yfinance) testleri
```

**Dev (2 process — hot reload):**
```bash
# Terminal 1 — backend
cd backend && uv run uvicorn sonar.api.app:create_app --factory --port 8000
# Terminal 2 — frontend (Vite, /api → :8000 proxy)
cd frontend && npm run dev
```

**Tek-process (build edilmiş frontend'i backend servis eder):**
```bash
cd frontend && npm run build
mkdir -p ../backend/sonar/web/static && cp -r dist/* ../backend/sonar/web/static/
cd ../backend && uv run sonar
```

**Tek-binary:**
```bash
# (statik build paket içine kopyalandıktan sonra, repo kökünde)
uv run pyinstaller sonar.spec --noconfirm   # → dist/sonar(.exe)
```

## Çalışma akışı (her milestone)
1. **Spec/ADR** — davranış `docs/superpowers/specs/`'te, kararlar `docs/adr/`'da. Karar
   değişirse önce ADR/spec güncellenir.
2. **Plan** — her milestone kendi planı (`docs/superpowers/plans/`), TDD task'lara bölünür.
3. **Branch** — milestone başına branch (`m1-...`), master'a doğrudan implement edilmez.
4. **TDD** — failing test → implement → green → commit. Test çıktısı pristine.
5. Milestone bitince → review → master merge. Takip: `docs/ROADMAP.md`.

## Kod kuralları
- **Domain dili = `CONTEXT.md`** — kod terimleri birebir oradan (Symbol/Money/Quote/Filer…).
- **Derin tool** (ADR-0003): tool hesaplanmış sonuç döner; sayı işi `analytics`'te, LLM'de değil.
- **Market = plugin** (ADR-0001/0005): dış kaynak ham şekli domain'e sızmaz (ACL); VO döner.
- Global metodoloji: YAGNI, surgical changes, deep modules (`~/.claude/CLAUDE.md`).

## Yeni market (plugin) eklemek
`MarketPlugin` Protocol'ünü (`backend/sonar/market/base.py`) implemente eden bir sınıf yaz;
sabit tool yüzeyini o borsa için doldur, veremediğin yeteneğe `Unsupported` fırlat;
registry'ye kaydet. Çekirdek/agent/UI değişmez. (TR örneği ileride ayrı paket.)
