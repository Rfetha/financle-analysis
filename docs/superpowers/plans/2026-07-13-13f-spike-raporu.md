# 13F Spike Raporu (B0) — 2026-07-15

> Plan Task B0. Gerçek SEC verisiyle ölçüldü; kod yazılmadı. Kullanıcı Faz B'yi delege etti
> ("sen faz b'yi bitir") → yol kararı bu raporun verisine göre **bulk index** olarak verildi.

## Ölçümler (2026 Q1 raporları = `01mar2026-31may2026`)

| Metrik | Değer |
|---|---|
| ZIP boyutu | 99.4 MB (Q1'26) · 90.3 MB (Q4'25) |
| INFOTABLE.tsv (açılmış) | **396 MB · 3,822,885 satır** |
| distinct CUSIP | 33,656 |
| SQLite'a tarama süresi | ~47 s (Python csv, tek geçiş) |
| CUSIP→ticker (naive isim eşleşmesi) | distinct **%36.3** · pozisyon-ağırlıklı **%54.4** · ticker-yönü **%56.4** |
| FIGI dolu | **%12.2** (468k/3.82M) |
| PUTCALL | LONG 3,682,720 · Put 66,994 · Call 73,171 (opsiyon ≈ %3.7) |
| ISAMENDMENT=Y | 441 filing |
| AMENDMENTTYPE | **RESTATEMENT 332 · NEW HOLDINGS 109** |
| company_tickers.json | 10,408 kayıt |
| **Spot-check** | NVDA `67066G104`, AAPL `037833100`, MU `595112103`, TSM `874039100`, BRK `084670702` → **5/5 VAR, doğru isim** |

## Kararlar

**1. Yol: BULK INDEX** (curated filer evreni DEĞİL).
Naive eşleşme %56 < %90 eşiği — ama eşik yanlış varsayıma dayanıyordu ("çıplak CUSIP gösterilemez").
Gerçek: **NAMEOFISSUER her satırda dolu**, yani gösterim asla CUSIP'e takılmaz (ticker biliniyorsa ticker,
bilinmiyorsa issuer adı). Likit/önemli ticker'lar (spot-check 5/5) çözülüyor → "NVDA'yı kim aldı" **çalışır**.
Veri de fizibıl (400MB/çeyrek, 47s). → bulk index doğru.

**2. CUSIP↔ticker haritası:** company_tickers.json isim-eşleşmesi (likit kapsam). Çıplak CUSIP hiç
gösterilmez — ticker yoksa `NAMEOFISSUER` fallback. Kapsam iyileştirme (ileride): SEC FTD dosyası
(CUSIP+SYMBOL doğrudan). FIGI **elendi** (%12 dolu, işe yaramaz).

**3. AÇIK FİLTRELEME KARARI → kapandı: ticker'a çözülen satırları tut.**
2 çeyrek × 3.8M = ~7.6M ham satır (~1GB) masaüstü için ağır. Ticker-çözülebilir satırlara filtrele
→ ~%56 → ~2.1M/çeyrek (~550MB, 2 çeyrek). Uzun-kuyruk (obscure/yabancı/tahvil) düşer — nadir sorulur,
zaten ticker'a çözülemez. "NVDA'yı kim aldı" etkilenmez (NVDA çözülür, satırı kalır). Sadece "filer'ın
TÜM portföyü" biraz eksik olur (kabul).

## B1+ için ZORUNLU schema/URL düzeltmeleri (plan yanlış varsaymıştı)

- **URL değişti:** `https://www.sec.gov/files/structureddata/data/form-13f-data-sets/{start}-{end}_form13f.zip`
  — çeyrek adı değil **tarih aralığı** (ör. `01mar2026-31may2026`), `/structureddata/` yolunda.
  Güncel liste: `https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets` sayfasından
  ilk iki `.zip` linki (en yeni iki dönem).
- **Filer adı `SUBMISSION`'da DEĞİL:** `SUBMISSION` = ACCESSION_NUMBER · FILING_DATE · SUBMISSIONTYPE ·
  **CIK** · PERIODOFREPORT. Filer **adı** → `COVERPAGE.FILINGMANAGER_NAME` (+ `AMENDMENTTYPE`, `ISAMENDMENT`).
  Join: ACCESSION_NUMBER üstünden INFOTABLE↔SUBMISSION(CIK)↔COVERPAGE(name, amendment).
- **INFOTABLE kolonları (doğrulandı):** ACCESSION_NUMBER · NAMEOFISSUER · CUSIP · FIGI · VALUE · SSHPRNAMT ·
  PUTCALL · … . Plan'daki alan adları (SSHPRNAMT/VALUE/PUTCALL/CUSIP/NAMEOFISSUER) **doğru**.
- **VALUE = dolar** (2023 kural değişikliği sonrası; artık bin-dolar değil).
- **ISAMENDMENT çoğu satırda boş** ('' ya da 'N'); yalnız 'Y' amendment. AMENDMENTTYPE değerleri:
  `RESTATEMENT` (eskiyi sil-yenile) · `NEW HOLDINGS` (ekle) — plan kuralı doğru.

## Sonraki
B1 ingestion: yukarıdaki URL/schema ile. B2 arka plan. B3-B6 analytics+tool. B7 recipe node. B8 frontend.
İndirilen test verisi: `%TEMP%\13f\` (repoya değil — gerçek-ingest testinde tekrar kullanılabilir).
