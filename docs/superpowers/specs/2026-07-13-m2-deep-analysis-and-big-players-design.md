# M2 — Deep Analysis + Big Players (tasarım)

> Durum: onaylandı (2026-07-13) · Kapsam: ROADMAP **M2** + **M4** (Big Players M2'ye alındı)
> Bağlam: [`ARCHITECTURE.md`](../../ARCHITECTURE.md) · [`CONTEXT.md`](../../../CONTEXT.md) · ADR-0001/0003/0005/0007/0008

## 1. Ne yapıyoruz

Tek hisse için **top-down derin analiz** (UC1) + **büyük oyuncular** (UC6'nın v1 çekirdeği):
makro → mikro → teknik → haber → kurumsal/insider akış → tek rapor + interaktif grafik + canlı fiyat.

Roadmap'te M2 ve M4 ayrıydı; ikisi de aynı EDGAR altyapısına (ticker↔CIK + rate-limitli istemci)
dayandığı ve kullanıcının asıl istediği çıktı ("BofA geçen çeyrek NVDA'ya girmiş") Big Players'ta
olduğu için **tek spec** altında birleştirildi. Yürütme **iki faz**, arada merge kapısı var.

### Faz A — Derin analiz *(shippable)*
Alpaca fiyat · EDGAR fundamentals · FRED makro · teknikler (elle) · haber · peers
→ DeepAnalysis recipe → rapor + Lightweight Chart + `/api/stream/quotes`.

**DoD:** `"NVDA"` → Makro/Mikro/Teknik/Haber bölümlü rapor + grafik. Sayılar tool çıktısıyla birebir.
Alpaca key'i olmadan da çalışır (kaynak şeridi görünür).

### Faz B — Big Players
13F (kurumsal pozisyon + çeyreklik Δ) · Form 4 (insider). Recipe'ye **bir node eklenir**, Faz A kodu
değişmez.

**DoD:** `"NVDA'yı geçen çeyrek kim aldı/sattı"` → filer + Δ lot + Δ% ; EDGAR'da elle doğrulanır.

---

## 2. Veri gerçeği (tasarımı belirleyen kısıt)

Ücretsiz-resmî dünyada **isim + miktar + aynı gün** diye bir veri **yoktur**. Üç ayrı şey vardır:

| Ne | Kaynak | Gecikme | **Kim** yazıyor mu |
|---|---|---|---|
| Kurumsal pozisyon (BofA, Berkshire) | SEC **13F-HR** | çeyreklik, **45 gün** | ✅ |
| Insider alım/satım (CEO, CFO) | SEC **Form 4** | **2 iş günü** | ✅ |
| %5 üstü pay | SEC **13D/13G** | günler | ✅ (→ v2) |
| Short interest (toplam açık pozisyon) | **FINRA** | ayda 2 kez | ❌ (toplam) |
| Hacim anomalisi | *iç hesap* (OHLCV) | günlük | ❌ |
| Günlük short volume · dark pool/ATS | FINRA | günlük / haftalık | ❌ → **v2, §9** |
| Gerçek zamanlı isimli akış | — | — | **yok** (ücretli veride bile) |

**Piyasa anonimdir.** Tape'e düşen kayıtta alan/satanın kimliği **yoktur** — ne bizde, ne Bloomberg'de.
"Kim aldı" sorusunun ücretsiz-resmî dünyada **iki** cevabı var: 13F (45 gün) ve Form 4 (2 gün). Başkası yok.

**Sonuç:** Sonar gecikmeyi **saklamaz, yazar**. Her Big Players çıktısı Provenance taşır:
*"13F · 2026-Q1 · 45 gün gecikmeli"*. Gecikmeli veri asla canlı gibi sunulmaz; isimsiz veri asla isimli
gibi ima edilmez. Retail sitelerinin "institutional flow" dediği şey ya 13F'tir (45 gün) ya da tape
çıkarımıdır (tahmin) — Sonar ikisini **ayrı satırda** gösterir.

**Günlük short volume ve dark pool/ATS neden alınmadı:** tipik bir S&P hissesinde günlük short volume
zaten **her gün %40-50**'dir (market maker envanter hedge'i "short" print'lenir) → "%44 short" bir sinyal
değil, normal bir salı. ATS dosyasındaki isim (*"UBS ATS"*) **venue**'dur, alıcı değil — "UBS aldı" diye
okunması en yaygın hatadır. Gürültülü ve yanlış-okunmaya açık veri için ingestion makinesi kurmuyoruz;
bütçe 13F Δ analitiğine ve insider cluster'a gidiyor (§7).

## 3. Kaynak seçimi

| Veri | Birincil | Fallback | Key |
|---|---|---|---|
| Fiyat / OHLCV / canlı tick | **Alpaca** (resmî API + WebSocket) | yfinance | ücretsiz, opsiyonel |
| Fundamentals | **SEC EDGAR companyfacts** (XBRL, denetlenmiş) | — | yok |
| Kurumsal pozisyon / insider | **SEC 13F / Form 4** | — | yok |
| Short interest / days-to-cover | **FINRA** (ayda 2 kez) | — | yok |
| Makro (faiz, TÜFE, 10Y) | **FRED** (key'siz CSV endpoint) | — | yok |
| Global rejim (VIX, DXY, emtia) | `GlobalMacro` (fiyat kaynağı üstünden) | — | yok |
| Peers | **EDGAR SIC** kodu | — | yok |
| Haber | RSS | Alpaca/Benzinga | yok |

**Neden Alpaca:** yfinance *gerçek* fiyat verisi verir ama Yahoo'nun özel endpoint'ini kazır —
sözleşmesiz, dokümansız, periyodik olarak kırılıyor, ToS'u dağıtılan bir üründe gri. Alpaca resmî,
versiyonlu, yazılı rate-limit'li ve **WebSocket** veriyor (canlı quote SSE'si polling'e mahkûm olmuyor).
Bedeli: ücretsiz key. **Alpaca fundamentals/holders vermez** — o sütunlar zaten EDGAR'da.

**Key akışı (sessiz düşme yok, ADR §5):** key yoksa uygulama çalışır, fiyat `Provenance = "yfinance
(resmî değil)"` taşır ve UI'da bir şerit çıkar: *"Fiyat Yahoo'dan kazınıyor — kırılgan. Ücretsiz Alpaca
key'i ile resmî veriye geç."* Öneri net, zorlama yok, hangi veriyle bakıldığı **her zaman** görünür.
Env: `SONAR_ALPACA_KEY` / `SONAR_ALPACA_SECRET` (M6'da Settings ekranı).

**EDGAR nezaketi (zorunlu):** `User-Agent: Sonar/<ver> (<email>)` + ≤10 req/s. İhlal = IP ban.
Merkezî `market/sources/http.py` uygular.

## 4. Mimari

### Kat ayrımı — tek cümlelik kural

> **Matematik ve orkestrasyon → çekirdek. "Hangi URL, hangi format" → plugin. "Nasıl HTTP çekilir" → ortak makine.**

```
analytics/          saf matematik (I/O yok)
  indicators.py     RSI · MACD · BB · EMA · S/R · OBV · hacim anomalisi
  holdings.py       (B) 13F Δ sınıflaması: new/exit/add/trim · float % · sahiplik trendi
  insiders.py       (B) Form 4 cluster tespiti
tools/              tool yüzeyi: Symbol → registry → plugin; hesap çekirdekte
  _cache.py         cached(key, ttl, fn) — 11 tool'un cache sarmalı tek yerde (Duplicated Code)
domain/             Candle · Fundamentals · NewsItem · MacroSnapshot · Signal · HoldingsSnapshot …
market/
  base.py           MarketPlugin (Protocol)  +  BaseMarketPlugin (opsiyonel ABC)  + Unsupported
  registry.py
  sources/          market bilmeyen ortak makine
    http.py         rate-limitli httpx (User-Agent, retry, backoff)
    rss.py          RSS → NewsItem
    global_macro.py VIX · DXY · WTI · altın · UST10Y  (her market kullanır)
  us/
    __init__.py     USMarketPlugin — ince composer
    prices.py       PriceSource Protocol → AlpacaPrices | YFinancePrices  (Strategy)
    edgar.py        ticker↔CIK · companyfacts · SIC · (Faz B) 13F/Form4
    finra.py        (B) short interest / days-to-cover
    fred.py         yerel makro seriler
    news.py         US feed listesi (parse ortakta)
agent/
  recipes/deep_analysis.py   deterministik StateGraph
```

Somut sınama: **`get_technicals` plugin'e hiç dokunmaz** — OHLCV'yi ister, RSI'ı `analytics`'te hesaplar.
TR plugin'i geldiğinde teknik analiz kodu tek satır değişmez. Portföy/watchlist/alert/brief de öyle
(ADR-0001: çekirdek, plugin değil).

### Plugin sözleşmesi: Protocol (sözleşme) + ABC (sözleşme bozunumu)

`MarketPlugin` **Protocol** kalır — sözleşme yapısal. Belirleyici sebep: `sonar-market-tr` **ayrı bir
pip paketi** olarak planlı (CLAUDE.md); üçüncü-parti paketin bizim base class'ımızdan türemek zorunda
kalması sıkı kuplajdır. Protocol'de böyle bir bağ yok.

`BaseMarketPlugin(ABC)` **opsiyonel batarya** olarak kalır, ama işi **Unsupported varsayılanları**:

```python
class BaseMarketPlugin(ABC):
    """11 yeteneğin Unsupported varsayılanı. Market yalnız verebildiğini override eder."""
    market: str
    def get_ohlcv(self, s, r, i):            raise Unsupported(f"{self.market}: ohlcv")
    def get_institutional_holders(self, s):  raise Unsupported(f"{self.market}: 13F")
    def get_short_interest(self, s):         raise Unsupported(f"{self.market}: short interest")
    ...
```

**Sakladığı karar:** *sözleşme nasıl bozunur* — ADR-0005'in "veremediğine `Unsupported` döner" kuralı
tek yerde, 11 kez tekrar edilmeden. TR plugin'i 4 yeteneği implement eder, kalan 7 otomatik `Unsupported`
döner. Protocol'de bu mümkün değil (eksik metot = `AttributeError`, sessiz çökme).

**Template Method KULLANILMIYOR** (ilk taslakta vardı, elendi). Deep-module denetimi: `get_macro_snapshot`
iskeleti 4 satır, sakladığı karar *"makro = global + yerel"* — interface ≈ implementation → **shallow**.
GoF kuralı da aynı yere çıkıyor: *adımlar inject edilebiliyorsa Template Method değil composition/Strategy.*
Ve inject edilebiliyor:

```python
class USMarketPlugin(BaseMarketPlugin):
    def __init__(self, prices: PriceSource, global_macro: GlobalMacro, local_macro: MacroSource, ...):
        self._prices, self._global, self._local = prices, global_macro, local_macro

    def get_macro_snapshot(self) -> MacroSnapshot:
        return MacroSnapshot(global_=self._global.snapshot(), local=self._local.snapshot())
```
`GlobalMacro` yine **tek yerde** (kopyala-yapıştır yok), ama kalıtım bağı da yok.

**Fiyat kaynağı = Strategy.** `PriceSource` Protocol'ü (`AlpacaPrices` | `YFinancePrices`); hangisi
kullanılacağı key'in varlığına göre **construction'da inject edilir**. Aynı interface, runtime'da değişen
davranış → GoF Strategy (Protocol ile, ABC'siz).

Rate-limitli HTTP ve RSS parser **miras verilmez, enjekte edilir** — onlar market davranışı değil altyapı;
base'e koymak "kod paylaşmak için kalıtım" (klasik anti-pattern) olurdu.

### Tool yüzeyi (ADR-0001: sabit sözleşme)

| Tool | Döner | Kaynak | Cache TTL |
|---|---|---|---|
| `get_quote(sym)` | fiyat + günlük % | Alpaca → yfinance | 60 sn |
| `get_ohlcv(sym, range, interval)` | mum serisi | Alpaca → yfinance | 15 dk / 12 sa |
| `get_technicals(sym)` | RSI · MACD · BB · EMA · S/R · **OBV + hacim/20g oranı** | *iç* (`analytics`) | 15 dk |
| `get_fundamentals(sym)` | değerleme · marj · büyüme · borç | EDGAR | 24 sa |
| `get_news(sym)` | başlık + kaynak + zaman | RSS | 15 dk |
| `get_macro_snapshot()` | faiz · TÜFE · 10Y · eğri · DXY · VIX | FRED + GlobalMacro | 6 sa |
| `get_peers(sym)` | aynı SIC'teki şirketler | EDGAR | 24 sa |
| `get_institutional_holders(sym)` *(B)* | filer + lot + değer + **Δ sınıflaması** + float % + sahiplik trendi | 13F | 24 sa |
| `get_insider_trades(sym)` *(B)* | insider işlemleri + **cluster tespiti** | Form 4 | 6 sa |
| `get_filer_holdings(filer)` *(B)* | bir filer'ın tüm pozisyonları | 13F | 24 sa |
| `get_short_interest(sym)` *(B)* | açık short + **days-to-cover** + float % | FINRA | 12 sa |

Tool'lar **hesaplanmış** sonuç döner (ADR-0003) — LLM aritmetik yapmaz. Market veremediğine
`Unsupported` (sessiz boş değil).

**Derinlik tool sayısında değil, tool'un içinde.** Faz B'nin asıl değeri yeni uç noktalar değil,
mevcutların içindeki analitik (hepsi `analytics/`'te, plugin'de değil):
- **13F Δ sınıflaması** — her filer için `new · exit · add · trim · hold`; float yüzdesi; kurumsal
  sahiplik trendi (*"%62 → %67; 47 filer girdi, 12 çıktı; en büyük artış: BofA +100M lot (yeni)"*).
- **Insider cluster** — *"son 30 günde 4 farklı yönetici açık piyasadan aldı, satan yok"*. Tek CEO alımı
  gürültü; küme alım, ücretsiz veride bulunan en sağlam sinyallerden biri (*cluster buying*).
- **Hacim anomalisi** — hacim / 20-gün ortalaması + OBV. Yeni kaynak gerektirmez, OHLCV'den çıkar.

## 5. DeepAnalysis recipe

`POST /api/analyze {ticker}` → **deterministik StateGraph, döngü yok** (ADR-0007):

```
            ┌─────────────── gather (LLM YOK) ────────────────┐
ticker ─▶   │ macro · fundamentals · ohlcv+technicals · news  │ ─▶ synthesize ─▶ SSE
            │ peers · (Faz B) big_players     — asyncio.gather│    tek LLM çağrısı,
            └────────────────────────────────────────────────┘    token-token akar
```

- **gather:** tool'lar paralel. Bir kaynak düşerse (EDGAR 500) **rapor düşmez** — o bölüm
  `unavailable` işaretlenir, synthesize "bu veri yok" der. Sessiz boşluk yok.
- **synthesize:** tek prompt, top-down şablon (Makro → Mikro → Teknik → Haber → *(B)* Big Players →
  Sentez). Prompt aritmetiği **yasaklar**; tüm sayılar `gather` çıktısında hazır.
- **Provider-bağımsız:** döngü yok, tool-calling gerekmiyor → local Qwen3 14B'de de birebir çalışır.
- **Yeni port yok:** `model.default_model()` zaten sentez portudur; recipe `model.astream(prompt)`
  çağırır. Ayrı bir `synthesize()` sarmalayıcı tek satırlık delegasyon = shallow module (POSD) → yazılmadı.

**Routing UI'da** (ADR-0007): LLM router yok. Chat ReAct'te kalır ve aynı deep tool'ları tekil çağırır.

## 6. API + SSE + frontend

| Uç | Şekil |
|---|---|
| `POST /api/analyze` | SSE: `analysis-step` → `chart` → `text-delta`* → `done` \| `error` |
| `GET /api/ohlcv/{ticker}?range=6mo` | JSON mum serisi (grafik bunu çeker) |
| `GET /api/stream/quotes?tickers=…` | SSE: `quote-tick` |

**Event taksonomisi genişler, yeniden yazılmaz** (ADR-0008): `analysis-step` · `chart` · `quote-tick`
eklenir; M1 tipleri aynen durur.

**Grafik:** `chart` part'ı yalnız `{ticker, range}` taşır; React bileşeni veriyi `/api/ohlcv` ile çeker
(SSE'ye 500 mum tıkıştırmıyoruz). Lightweight Charts + hesaplanmış gösterge overlay'leri.

**Canlı fiyat:** Alpaca WebSocket varsa abone olup fan-out; yoksa 15 sn polling. İki yolun çıktısı da
aynı `quote-tick` — frontend farkı bilmez.

## 7. Faz B — Big Players: önce ölç, sonra kur

SEC "NVDA'yı kim tutuyor" diye **ters indeks vermez** (13F filer başına dosyalanır) ve 13F'te **ticker
yok** — sadece CUSIP (lisanslı kimlik) + şirket adı. Ücretsiz-resmî çıkış: SEC'in *fails-to-deliver*
dosyalarında CUSIP + SYMBOL birlikte yayınlanıyor. **Bu bir varsayım — ölçmeden kod yazılmaz**
(M6'daki "önce ölç, sonra kur" disiplininin aynısı).

**Task B0 — spike (kod yok, ölçüm):**
1. DERA çeyreklik 13F veri seti (`SUBMISSION.tsv` + `INFOTABLE.tsv`) → kaç satır, kaç MB, SQLite'a
   yükleme süresi?
2. **CUSIP→ticker eşleşme oranı** (FTD dosyası ile). Eşik: **%90+**.
3. İki çeyreği yan yana koyup NVDA'da bilinen bir filer'ın Δ'sını **elle doğrula**.

**Spike kararı verir:**
- **Geçerse → toplu indeks.** ZIP → SQLite `holdings(cusip, filer_cik, quarter, shares, value)`.
  "Kim tutuyor" = SQL, *tüm* filer'lar. `get_filer_holdings` bedava gelir.
- **Geçmezse → küratörlü filer evreni.** ~50 CIK (Berkshire, BofA, Citadel, BlackRock…) — sadece
  onların 13F'i. Dataroma'nın yaptığı da bu. Kapsam dar, sinyal aynı.

**Form 4 spike'a bağlı değil** — per-ticker: issuer CIK → filing listesi → XML parse. 2 gün gecikmeli,
gerçek isim.

**Short interest spike'a bağlı değil** — FINRA'nın ayda 2 kez yayımladığı dosya, tek parse
(`market/us/finra.py`). Days-to-cover = açık short / ortalama günlük hacim → `analytics`.

**Bütün hesap `analytics/`'te**, plugin'de değil — her market için aynı matematik:
`holdings.py` (Δ sınıflaması, float %, sahiplik trendi) · `insiders.py` (cluster) · `indicators.py`
(hacim anomalisi).

## 8. Test stratejisi

- **Deterministik unit (varsayılan):** `analytics` göstergeleri **elle hesaplanmış referans değerlere**
  karşı (kütüphaneye değil, bilinen seriye); tool'larda cache hit/miss · `Unsupported` · **kısmi hata**
  (gather'da bir kaynak düşünce rapor ayakta mı); recipe node sırası fake model ile.
- **`@pytest.mark.slow`:** gerçek Alpaca/EDGAR/FRED — dış sözleşme hâlâ geçerli mi (yfinance
  kırılganlığının erken uyarısı burada çıkar).
- **`test_layering.py` genişler:** `analytics/` + `market/sources/` de provider-ithali yasağına girer;
  ayrıca `market/` içinde `analytics` matematiğinin tekrarlanmadığı (import yönü) kontrol edilir.

## 9. Kapsam dışı (bu spec'te yok)

- **Gerçek zamanlı isimli akış** — ücretli veride bile yok (piyasa anonim, §2).
- **Günlük short volume · dark pool/ATS** (FINRA) → **v2**. Veri ücretsiz ve mevcut; alınmama sebebi
  maliyet değil **yanlış-okunabilirlik**: günlük short volume tipik bir S&P hissesinde her gün %40-50
  (MM hedge print'i), ATS'teki isim venue'dur alıcı değil. v2'de, ne olmadığını doğru anlatan bir UI ile.
- **Opsiyon akışı** — ücretli (OPRA), non-goal.
- 13D/13G (v2) · ETF holdings (v2) · `search_symbols` fuzzy çözümleme (ayrı iş) · Settings ekranı (M6) ·
  portföy/watchlist (M3).

## 10. ADR etkisi

Yeni ADR gerekmiyor; mevcutlar korunuyor. İki ADR'ye **not** düşülecek:
- **ADR-0005** (market plugin): sözleşme = `MarketPlugin` Protocol; `BaseMarketPlugin` ABC yalnız
  **Unsupported varsayılanlarını** taşır (Template Method değil). Fiyat kaynağı seçimi = Strategy.
- **ADR-0001/0003:** tool yüzeyi bu spec'teki 10 tool'a genişledi; hesap `analytics/`'te.
