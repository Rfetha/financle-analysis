# Sonar — US Equity Research & Portfolio Agent

> Tasarım dökümanı (v1 — **usage / use-case odaklı**). Tarih: 2026-06-27
> Tech stack bilinçli olarak ertelendi (bkz. §10). Önce *ne yapacağı* kilitleniyor.

---

## 0. Tek cümle

Açık kaynak (OSS), provider-bağımsız, otonom çalışabilen bir **ABD borsası** araştırma
asistanı: portföyünü ve takip listeni izler, tek bir hisseyi (teknik + temel +
"büyük oyuncular" + haber) derinlemesine araştırır, her sabah otonom brief üretir.

## 1. Kapsam & felsefe

- **US-first.** ABD hisseleri + ABD ETF'leri. TR (BIST/TEFAS) **v1'de yok** — ileride
  ayrı bir plugin paketi olarak gelir (§2).
- **OSS, global.** Herkes kendi anahtarını / kendi modelini getirir. Repo'da sır yok.
- **Provider-bağımsız beyin.** Aynı sistem local open-weight model (Ollama) ile de,
  Claude/GPT API ile de çalışır. Kullanıcı seçer.
- **Lazy v1.** Üç alanı da (derin analiz / portföy+otonomi / büyük oyuncular) kapsar
  ama her birini **ince ve sağlam** tutar. Derinleşme v2.

### Non-goals (v1)
- Emir iletimi / broker entegrasyonu (al-sat yapmaz). Sadece analiz/izleme.
- Opsiyon akışı, dark pool, tick-level veri (çoğu ücretli — v2/atla).
- Çoklu kullanıcı / auth / abonelik / SaaS. Tek kullanıcı, lokal.
- Yatırım tavsiyesi iddiası. Bilgi + analiz üretir, karar kullanıcının.

---

## 2. Çekirdek mimari ilke: **tool'lar sabit, borsalar plugin**

Agent'ın gördüğü **tool yüzeyi sabit bir sözleşmedir.** Her borsa/market o sözleşmeyi
dolduran bir **plugin**'dir. Çekirdek, hangi market'in bağlı olduğunu bilmez.

```
            Agent (beyin)
                │  sabit tool sözleşmesi (değişmez)
        ┌───────┴────────┐
   market registry (plugin loader)
        │
   ┌────┴─────┐
   US plugin   [TR plugin — sonra, ayrı pip paketi]
   EDGAR·yfinance·FRED   KAP·TEFAS·TCMB
```

- v1 yalnız **US plugin** ile gelir.
- TR plugin sonra `financle-market-tr` gibi ayrı paket; çekirdek değişmez.
- Bir plugin bir yeteneği veremiyorsa **`unsupported`** döner — sistem çökmez,
  agent bunu görür ("bu market'te insider verisi yok").
- **Portföy / watchlist / alert / brief market'ten bağımsızdır** (lokal SQLite).
  Bunlar plugin değil, çekirdek.

### Sabit tool yüzeyi (capability contract)

| Tool | Ne döner | US kaynağı |
|---|---|---|
| `search_symbols(q)` | sembol çözümleme | yfinance / EDGAR ticker map |
| `get_quote(sym)` | anlık fiyat + günlük değişim | yfinance → Stooq |
| `get_ohlcv(sym, range, interval)` | fiyat serisi (grafik/teknik) | yfinance → Stooq |
| `get_fundamentals(sym)` | değerleme, bilanço, büyüme, marj | **SEC EDGAR companyfacts** + yfinance |
| `get_technicals(sym, [ind])` | RSI/MACD/BB/EMA/destek-direnç (hesaplı) | iç hesap (OHLCV üstünden) |
| `get_news(sym\|q)` | haber + sentiment | RSS / Finnhub |
| `get_institutional_holders(sym)` | kurumlar ne tutuyor + çeyreklik Δ | **SEC 13F** |
| `get_insider_trades(sym)` | yönetici alım/satım | **SEC Form 4** |
| `get_filer_holdings(filer)` | bir fonun tüm portföyü | **SEC 13F** |
| `get_etf_holdings(sym)` | ETF içeriği (top holdings + ağırlık) | yfinance / EDGAR N-PORT |
| `get_macro(series)` | tek makro seri (faiz, TÜFE, vb.) | **FRED** |
| `get_macro_snapshot()` | derlenmiş makro panosu (faiz, enflasyon, 10Y, getiri eğrisi, DXY, VIX) | **FRED** + yfinance |
| `get_peers(sym)` | sektör/rakip eşlikçiler (mikro karşılaştırma için) | yfinance / EDGAR SIC |

> Teknik/portföy hesapları (RSI, P&L, korelasyon, konsantrasyon) **market plugin'inde
> değil çekirdekte** — her market için aynı matematik.

> **Ticker bulma:** kullanıcı genelde "AAPL" değil "Apple" yazar. `search_symbols`
> isim/kısmi/fuzzy → ticker çözmeli (veri: SEC `company_tickers.json` CIK↔ticker↔isim +
> lokal fuzzy eşleşme). Agent, girdi temiz ticker değilse **önce** `search_symbols` çağırır.

---

## 3. Use-case'ler (her birine başarı kriteri)

Başarı kriterleri kasıtlı olarak "verifiable goal" formatında: bağımsız test edilebilir.

### Analiz katmanları (top-down: makro → mikro → teknik)

Her derin analiz üç katmanda yürür; agent yukarıdan aşağı bağlar:

- **Makro** — ekonomi/sektör rejimi: faiz, enflasyon, getiri eğrisi, DXY, VIX, sektör
  rotasyonu. Kaynak: `get_macro_snapshot` / `get_macro`. Soru: "ortam bu hisseye lehte mi?"
- **Mikro** — şirket + sektör konumu: değerleme, büyüme, marj, rakip kıyas. Kaynak:
  `get_fundamentals` + `get_peers`. Soru: "şirket sektöründe nerede, ucuz/pahalı mı?"
- **Teknik** — fiyat aksiyonu: trend, momentum, destek/direnç. Kaynak: `get_technicals`.
  Soru: "giriş/çıkış zamanlaması ne diyor?"

### UC1 — Tek hisse derin analiz  *(v1)*
**Akış:** kullanıcı "NVDA analiz et" → agent şu tool'ları çağırır: `get_macro_snapshot`,
`get_fundamentals`, `get_peers`, `get_ohlcv`, `get_technicals`,
`get_institutional_holders`, `get_insider_trades`, `get_news` → tek yapılandırılmış
rapor + 1 grafik.
**Rapor bölümleri (top-down):** Özet · **Makro bağlam** (rejim, hisseye etkisi) ·
**Mikro/Temel** (değerleme, büyüme, marj, rakip kıyas) · Teknik (trend, sinyal,
destek/direnç) · Büyük oyuncular (kurumsal Δ + insider) · Haber/sentiment · Riskler.
**Başarı:** Rapordaki sayılar tek tek kaynakla doğrulanabilir; grafik render olur;
veri eksikse bölüm "veri yok" der, uydurmaz.

### UC2 — Portföy paneli  *(v1)*
**Akış:** pozisyon ekle (ticker, lot, maliyet) → canlı değer, unrealized P&L,
varlık dağılımı, konsantrasyon riski, pozisyon başı hızlı sinyal.
**Başarı:** P&L elle hesapla → eşleşir; tek varlık ağırlığı eşiği aşınca flag.

### UC3 — Watchlist  *(v1)*
**Akış:** sahip olmadığın tickerlar → fiyat / Δ / sinyal / son haber board'u.
**Başarı:** tek bakışta board; manuel yenileme + otomatik (brief ile birlikte).

### UC4 — Otonom günlük brief  *(v1)*
**Akış:** her sabah (cron) agent derler: portföy gecelik hareket + watchlist öne
çıkanlar + tetiklenen alertler + **senin hisselerinde yeni 13F/insider filing**.
"Brief" sayfasına yazar (+ opsiyonel push).
**Başarı:** kullanıcı uygulamayı açmadan brief oluşur; içerik kullanıcının kendi
hisselerine özel (genel piyasa spam'i değil).

### UC5 — Alert  *(v1, ince)*
**Tetikleyiciler:** fiyat eşiği · RSI aşırı alım/satım · "insider senin
watchlist'indeki hisseyi aldı" · "bir fon pozisyon açtı/kapadı (13F)".
**Başarı:** koşul başına 1 kez tetikler (cooldown); UI'da görünür; brief'e düşer.

### UC6 — Büyük oyuncu gezgini  *(v2 — derin)*
**Akış:** fon seç (örn. bir 13F filer) → portföyü + çeyreklik değişim tablosu;
ya da hisse seç → kim topluyor / kim boşaltıyor + insider zaman çizelgesi.
**Başarı:** EDGAR / Dataroma ile eşleşir.
**Not:** v1'de bu verinin *çekirdeği* zaten var (`get_institutional_holders`,
`get_filer_holdings`); v6 sadece bunun zengin gezinti UI'ı.

### UC7 — Chat (omurga)  *(v1)*
**Akış:** serbest soru ("NVDA vs AMD temel karşılaştır", "geçen çeyrek TSLA'yı en
çok kim aldı") → agent uygun tool'ları çağırır → veriye dayalı cevap.
**Başarı:** cevaplar tool çıktısına dayanır; kaynak/sayı gösterir; halüsinasyon yok.
Aynı tool'lar hem chat'ten hem panel butonlarından çağrılır (tek yol).

**v1 kesimi:** UC1, UC2, UC3, UC4, UC5, UC7. **UC6 → v2.**

---

## 4. "Büyük oyuncular" — bu projenin farklılaştırıcısı

ABD'de bu veri **ücretsiz ve resmî** (TR'de KAP PDF kazımak gerekiyordu; US'te API).

| Sinyal | Kaynak | Sıklık | Tool |
|---|---|---|---|
| Kurumsal pozisyonlar | SEC **13F-HR** | çeyreklik | `get_institutional_holders`, `get_filer_holdings` |
| Yönetici alım/satım | SEC **Form 4** | gün içi (filing oldukça) | `get_insider_trades` |
| Aktivist / %5+ pay | SEC **13D/13G** | olay bazlı | (v2 — `get_large_stakes`) |
| ETF içerik değişimi | N-PORT / yfinance | aylık/çeyreklik | `get_etf_holdings` |

**Türetilmiş içgörüler (çekirdekte hesaplanır):** çeyreklik "yeni açılan / kapatılan /
artırılan / azaltılan" pozisyonlar; bir hissede net kurumsal akış; insider net alım baskısı.

---

## 5. Otonomi modeli

- **Tetik:** arka plan scheduler (cron benzeri). Sabah 1×, gün içi alert taraması N dk'da bir.
- **Çıktı:** Brief sayfası (UI), alert listesi, opsiyonel push (e-posta/Telegram — v2).
- **Beyin:** otonom işler için **local model (Ollama) varsayılan** — bedava, ToS sorunu
  yok, sürekli çalışmaya uygun. Zor analizde Claude/GPT'ye yükseltilebilir (kullanıcı açarsa).
- **Manuel mod:** UI açıkken kullanıcı aynı işleri elle tetikler (chat / butonlar).

---

## 6. Veri saklama & memory

- **Yapılandırılmış veri → SQLite.** portföy, watchlist, alert, brief geçmişi, filing
  snapshot'ları, fiyat/haber cache. Tek dosya, taşınabilir, OSS dostu.
- **Tam metin arama → SQLite FTS5** (haber/filing içinde arama). Ayrı servis yok.
- **Vector DB → v1'de YOK.** Gerçek bir semantik arama ihtiyacı doğarsa `sqlite-vec`
  uzantısı (yine tek SQLite dosyası). Ayrı Chroma/Pinecone/Weaviate **YAGNI**.
- **Agent "hafızası":** kullanıcı tercihleri + ek bağlam düz markdown/JSON dosyada
  (versiyon kontrolüne girebilir, debug edilebilir). Embedding gerektirmez.

> Karar: **SQLite (+FTS5, gerekirse sqlite-vec)**. Ayrı vektör veritabanı kurma.

---

## 7. Bileşen sınırları (her biri tek iş, bağımsız test edilebilir)

| Bileşen | İşi | Bağımlılığı |
|---|---|---|
| `market` (plugin) | sabit tool yüzeyini bir borsa için doldurur | dış API'ler |
| `analytics` | teknik sinyaller + portföy/risk matematiği | OHLCV (market'ten) |
| `store` | SQLite repo'lar (portföy/watchlist/alert/brief/cache) | SQLite |
| `agent` | tool loop, model-bağımsız | tool yüzeyi + store |
| `scheduler` | otonom brief + alert değerlendirme | agent + store |
| `web` | UI (chat + paneller + grafik) | agent + store |

---

## 8. Hata felsefesi (kısa)

- Market plugin bir kaynağı veremezse → `unsupported` / `provenance` ile temiz dönüş,
  agent bunu kullanıcıya söyler. Sessiz boş cevap yok.
- Dış API hatası → fallback zinciri (yfinance→Stooq); zincir biterse hata kodu döner.
- Agent veri yoksa **uydurmaz**; "veri bulunamadı" der (UC1/UC7 başarı kriteri).

---

## 9. v1 → v2 yol haritası (özet)

- **v1:** US plugin · UC1–5 + UC7 · Vite+React web (SSE streaming, ADR-0008) · SQLite · LangGraph beyin (Claude/GPT/local) · sabah brief.
- **v2:** UC6 derin gezgin · 13D/13G · screener tool · push bildirim (Telegram/e-posta) ·
  generative UI (CopilotKit/AG-UI) · TR plugin paketi · backtesting.

---

## 10. KARARLAŞTI — tech stack (kaynak: `docs/adr/`)

| Eksen | Karar | ADR |
|---|---|---|
| Dil & şekil | Python core + TS/React UI, monorepo, OS-başına tek-binary (PyInstaller) | 0001 |
| Backend | FastAPI | 0001 |
| Frontend / streaming | Vite+React+TS SPA (SSR yok); SSE uniform (chat + canlı-quote), AG-UI-ready | 0008 |
| Agent framework | LangGraph (+LangChain), provider-agnostic; chat=ReAct, recipe=StateGraph | 0006/0007 |
| AI sağlama | tek swappable provider: ChatGPT/Codex-OAuth · Claude (Claude Code üzerinden) · API key; local sonra | 0002 |
| Tool felsefesi | derin tool — sayı çekirdekte, LLM yalnız sentez | 0003 |
| Tool taşıma | MCP server (Claude Code/OAuth yolu için) + LangGraph agent'a doğrudan — aynı sabit yüzey | 0001/0002 |
| Saklama | tek SQLite (DB + cache + history + FTS5), WAL; Redis yok; vector DB yok (`sqlite-vec` sleeper) | 0004 |
| Veri kaynağı v1 | yfinance(+Stooq) · SEC EDGAR · FRED · haber RSS/Finnhub; Polygon/AlphaVantage sonra plugin | — |
| Dağıtım | CI (GitHub Actions) OS-matrix → binary'ler siteye; ikincil `uv tool`/pipx; üçüncül Docker | 0001 |

---

## 11. Açık sorular (kullanıcı onayı bekleyen)

1. Use-case kesimi (UC1–5+UC7 v1, UC6 v2) onaylandı mı?
2. Sabit tool yüzeyinde eksik var mı? (örn. v2 için `run_screener`, `get_large_stakes`)
3. Non-goals listesi doğru mu? (özellikle "broker/emir yok" — sadece analiz)
