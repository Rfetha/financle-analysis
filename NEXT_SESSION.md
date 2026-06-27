# Next Session — Buradan devam et

> Bir sonraki oturum için handoff. Tam bağlam: `CLAUDE.md` · `docs/ROADMAP.md` · `docs/adr/`.

## Nerede kaldık (2026-06-27)

**M0 (walking skeleton) DONE & master'a merge'li.** Çalışan ürün: `cd backend && uv run sonar`
→ tarayıcı → ticker yaz → canlı fiyat. 18 test geçiyor. Apache-2.0 lisanslı.

- Mimari/kararlar tam dökümante: spec + domain-model + **8 ADR** + ROADMAP.
- Tüm tech stack kilitli (Python/FastAPI/LangGraph/SQLite/Vite+React/uv/PyInstaller — bkz CLAUDE.md).
- Bug fix merge'li: bilinmeyen ticker → 404 (eski 500 değil).

## Hemen sıradaki iş (bu sırayla)

1. **UI design pass** — `impeccable:frontend-design` skill'i, yön = **TradingView-vari**
   (koyu/modern/data-dense; memory'de kayıtlı: `ui-design-direction`). Çıktı: tasarım sistemi
   + v1 ekran wireframe'leri (chat · portföy dashboard · watchlist · deep-analysis raporu · grafik).
2. **M1 (Agent omurgası)** — `writing-plans` ile plan yaz, sonra `subagent-driven-development`.
   M1 içeriği: LangGraph chat (ReAct) + `/api/chat` **SSE** + chat kutusu + MessagePart/registry
   (ADR-0008). UI design pass'inin çıktısına giydirilir.

## M1 ÖNCESİ düzeltilecek (M0 final review bulguları)
1. **Paylaşılan `sqlite3.Connection`** → per-request/thread-local (concurrent SSE + tool çağrıları yarışmasın). **[Important]**
2. ~~Geçersiz ticker → 500~~ ✅ ÇÖZÜLDÜ (UnknownSymbol → 404).
3. `@types/react` v19 ↔ React 18 runtime → pin.
4. `sonar.spec` hiddenimports'a `httpx` ekle (temiz makinede binary doğrula).
5. `test_static.py` else-branch tautology → `pytest.skip`.
6. Kozmetik Minor'lar (kullanılmayan import, type annotation, yfinance API yorumu) → M1 CI/lint pass.

## Çalıştırma / test / build
```bash
cd backend && uv run pytest          # testler (18 passed)
cd backend && uv run pytest -m slow  # gerçek yfinance
cd backend && uv run sonar           # uygulama (tek process)
# dev 2-process + binary build: bkz CONTRIBUTING.md
```
⚠️ `dist/sonar.exe` fix'ten ÖNCE build edildi (eski 500 bug'lı). Fix'li binary için yeniden build.

## Branch durumu
- `master` = ana hat (M0 + fix + LICENSE).
- `m0-walking-skeleton`, `fix/quote-robustness-and-license` = merged, silinebilir.

## Açık karar yok
LICENSE seçildi (Apache-2.0). UI yönü seçildi (TradingView-vari). M1 planı + UI design pass başlatılmayı bekliyor.
