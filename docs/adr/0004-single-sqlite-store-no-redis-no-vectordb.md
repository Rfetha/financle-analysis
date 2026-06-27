# 0004 — Tek SQLite: DB + cache + history + FTS; Redis yok, vector DB yok

Sonar lokal tek-kullanıcı bir app olduğu için **tüm saklama tek SQLite dosyasında**:
kullanıcı/app state (portföy, watchlist, alert, brief), snapshot history (13F/insider),
**TTL'li cache tablosu** ve **FTS5** tam-metin arama. **WAL modu** açık (web-reader +
scheduler-writer çakışmasın).

## Considered Options
- **Redis cache:** reddedildi — ekstra servis + ops, tek-binary dağıtımı bozar, tek
  kullanıcıda ölçülebilir fayda yok. Cache bir **arayüz** arkasında durur; gerçekten
  çok-kullanıcı olunursa Redis impl'i o zaman takılır.
- **Ayrı vector DB (Chroma/Pinecone):** reddedildi — hiç gerekmez; lazım olursa
  `sqlite-vec` uzantısı aynı dosyaya eklenir.

## Vektör arama — "sleeper" (v1'de YOK)
v1'de vektör/embedding yok; arama = **FTS5 (keyword)**. Başlangıçta marjinal fayda ≈ 0
(corpus boş, user memory küçük/yapılı), maliyet > 0 (embedding modeli + ingest + şema).
**Tetik:** corpus büyüyüp semantik aramanın keyword'ü gözle görülür yendiği gün →
`sqlite-vec` aynı dosyaya eklenir. Bugün hiçbir şey yapmadan kapı açık.

## Consequences
- Sıfır ek servis; tek dosya taşınır/yedeklenir.
- WAL şart (eşzamanlı okuma/yazma).
- Cache + (gelecekteki) vektör aynı arayüz/dosya disiplininde → ileride swap ucuz.
- Opsiyonel mikro-opt: en sıcak anahtarlar için in-memory TTLCache — yalnız ölçülürse.
