# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Durum: design-first, henüz kod yok

Bu repo şu an **implementasyon öncesi** fazda. Kod, build/lint/test komutu, paket
manifesti **yok**. Tek kaynak gerçeği tasarım spec'i:

- **Spec:** `docs/superpowers/specs/2026-06-27-financle-us-equity-agent-design.md`

Yeni bir iş yapmadan önce o spec'i oku. Komut/araç eklendikçe bu dosyayı güncelle
(şu an uydurma komut yazma).

## Proje ne (özet)

**Sonar** — OSS, provider-bağımsız, otonom çalışabilen bir **ABD borsası** araştırma
asistanı. Portföy + watchlist izler, tek hisseyi (teknik + temel + "büyük oyuncular" +
haber) derinlemesine araştırır, sabah otonom brief üretir.

## Kilitlenen kararlar (spec'ten — bunları bozma, değişiklik gerekirse spec'i güncelle)

- **US-first.** ABD hisse + ETF. TR (BIST/TEFAS) v1'de YOK → ileride ayrı plugin paketi.
- **Çekirdek ilke: tool yüzeyi sabit, borsalar plugin.** Agent'ın gördüğü ~11 tool'luk
  sözleşme değişmez; her market (US plugin v1) o sözleşmeyi doldurur. Veremediği yeteneğe
  `unsupported` döner, çökmez. Portföy/watchlist/alert/brief market'ten bağımsız (çekirdek).
- **Provider-bağımsız beyin.** Aynı sistem local open-weight (Ollama) / Claude / GPT ile
  çalışır. Otonom işlerde varsayılan local model (bedava, ToS sorunu yok).
- **OAuth notu:** Anthropic abonelik OAuth'u yalnız Claude Code'da meşru; Agent SDK /
  3rd-party'de API key gerekir. Bu yüzden OAuth mimari direk değil, "Claude Code içinde
  çalıştır" dipnotu.
- **Storage: SQLite** (+FTS5; gerekirse `sqlite-vec`). **Ayrı vector DB YOK** (YAGNI).
- **"Büyük oyuncular" = SEC EDGAR** (13F kurumsal, Form 4 insider) — US'te bedava/resmî.
- **Use-case kesimi:** UC1 (derin analiz), UC2 (portföy), UC3 (watchlist), UC4 (otonom
  brief), UC5 (alert), UC7 (chat) → **v1**. UC6 (büyük oyuncu gezgini derin) → v2.
- **Non-goal:** broker/emir iletimi YOK (al-sat yapmaz, sadece analiz/izleme). Çoklu
  kullanıcı/auth/SaaS yok. Opsiyon akışı/dark pool yok (ücretli).
- **Tech stack ERTELENDİ.** Eğilimler (kilit değil): Python · web UI (NiceGUI adayı,
  lokal start→tarayıcı) · generic agent loop (Pydantic-AI/LangGraph). Sonraki dökümanda
  netleşecek.

## Metodoloji

Global `~/.claude/CLAUDE.md` (Universal Coding Methodology) bu projede geçerli:
YAGNI, surgical changes, deep modules, "tool'lar sabit / market plugin" sınırına sadık kal.
