# Sonar

Sonar, ABD borsası için kişisel ve otonom çalışabilen bir araştırma + portföy-izleme
asistanıdır. Bu dosya projenin alan dilini (ubiquitous language) sabitler — yalnız
sözlük, implementasyon detayı içermez.

## Language

**Position**:
Kullanıcının sahip olduğu tek menkul kıymet kaydı (sembol + lot + maliyet).

**Portfolio**:
Kullanıcının sahip olduğu Position'ların bütünü.
_Avoid_: hesap, account

**Watchlist**:
Kullanıcının sahip olmadığı ama izlediği sembollerin listesi.
_Avoid_: takip listesi

**Market**:
Menkul kıymetlerin ait olduğu borsa/yargı bölgesi (v1: US); analiz yetenekleri Market'e göre değişir.
_Avoid_: exchange, borsa

**Big Players**:
Bir hissede etkili büyük aktörler; iki türü var: **Institutional Holder** ve **Insider**.
_Avoid_: smart money, whale

**Institutional Holder**:
Bir hissede çeyreklik raporlanan kurumsal pozisyon sahibi (fon, hedge fund).

**Insider**:
Şirketin yöneticisi/yönetim kurulu üyesi; alım-satımı resmî bildirilir.

**Filer**:
Tüm portföyünü çeyreklik bildiren kurumsal aktör; holdings'i bir bütün olarak incelenir.

**Signal**:
Bir sembol için hesaplanan, [-1, +1] arası yönlü gösterge (teknik veya sentiment).

**Deep Analysis**:
Tek bir hisse için Macro + Micro + Technical + Big Players + haber'i birleştiren tek çıktı.

**Brief**:
Otonom üretilen günlük özet (portföy hareketi + watchlist + tetiklenen Alert + yeni filing).
_Avoid_: rapor, digest

**Alert**:
Önceden tanımlı bir koşul gerçekleşince üretilen bildirim.

**Symbol**:
Bir Market'teki menkul kıymetin tanımlayıcısı (ticker + Market); kodda ham `str` değil.

**HoldingsSnapshot**:
Bir Filer'ın belirli bir Period'daki tüm pozisyonlarının değişmez fotoğrafı (13F).

**HolderPosition**:
Bir HoldingsSnapshot içindeki tek pozisyon (Symbol + adet + değer + ağırlık).

**Provenance**:
Dışarıdan gelen her verinin kaynağı + çekilme zamanı.

**Quote**:
Bir Symbol'ün anlık fiyatı + günlük % değişimi + Provenance'ı. Değişmez; Market'ten gelir, hesaplanmış
gelir (ham tick değil).

**Deep Tool**:
Ajanın çağırdığı, **hesaplanmış ve yapılandırılmış** sonuç dönen tool. "Derin" = işi tool yapar, model
yalnız sentezler; ham veri döndüren tool sığdır ve kabul edilmez.

**Unsupported**:
Bir Market'in veremediği yetenek için dönen açık cevap. Sessiz boş sonuç değil — "bu borsa bunu vermiyor"
demenin resmî yolu.

### Analiz katmanları
**Macro**: Ekonomi/sektör rejimi (faiz, enflasyon, getiri eğrisi, DXY, VIX).
**Micro**: Şirket + sektör konumu (değerleme, büyüme, marj, rakip kıyas).
**Technical**: Fiyat aksiyonu (trend, momentum, destek/direnç).

## Relationships
- A **Deep Tool** returns a computed result (e.g. a **Quote**) or **Unsupported**
- A **Portfolio** holds many **Positions**
- A **Position** / **Watchlist** entry references one symbol in one **Market**
- **Big Players** = **Institutional Holders** + **Insiders** for a symbol
- A **Filer** holds many **Institutional Holder** positions across symbols
- A **Deep Analysis** combines **Macro** + **Micro** + **Technical** + **Big Players** + news
- A **Brief** aggregates **Portfolio** moves + **Watchlist** + triggered **Alerts** + new filings

## Example dialogue
> **Dev:** "Brief'e 'yeni filing' düşünce bu Insider mı Institutional Holder mı?"
> **Domain:** "İkisi de olabilir — Big Players'ın herhangi biri. Ama Insider gün içi,
> Institutional Holder çeyreklik gelir; Brief ikisini ayrı satırda gösterir."

## Flagged ambiguities
- **"Fund"** iki şeye işaret ediyordu: kullanıcının **Portfolio**'su vs bir **Filer**
  (kurumsal fon). Çözüm: kullanıcının olan = **Portfolio**, 13F bildiren = **Filer**;
  "fund" kelimesini tek başına kullanma.
- **"Holdings"** hem **ETF** içeriği hem **Institutional Holder** pozisyonları için
  kullanılıyordu. Çözüm: "ETF holdings" vs "Institutional Holder positions".
- **"Big players"** bulanıktı → **Institutional Holder + Insider** olarak sabitlendi.
