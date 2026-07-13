# Model katmanı: OpenRouter · local · API key — tasarım

**Tarih:** 2026-07-13 · **Durum:** onay bekliyor · **İlgili:** ADR-0002 (provider), ADR-0007 (agent mimarisi)

## Problem

M1'de chat iki yoldan koşabiliyordu: Claude aboneliği (Claude Code SDK döngüyü sürer) ve API key
(LangGraph ReAct). Bu iki-loop'lu yapının üç maliyeti var:

1. **Versiyon kayması** — SDK API'si ve `claude` CLI davranışı bizim kontrolümüzde değil; her sürüm
   aynı davranmayabilir. Uygulamanın çekirdek akışı dış bir binary'nin davranışına bağlı.
2. **Politika kayması** — Anthropic Haziran 2026'da Agent SDK kullanımını ayrı kredi havuzuna almayı
   denedi, geri çekti ama "yeniden kurgulayacağız" dedi. Fatura modeli değişebilir.
3. **Davranış ikiliği** — hafıza, onay kapısı, döngü müdahalesi provider'a göre farklı yerlerde yaşar;
   "her provider'da aynı" garantisi verilemez.

Aynı zamanda kullanıcının Claude/ChatGPT aboneliğinden değer üretmek isteniyor — ama abonelik OAuth
token'ını kendi loop'umuzda kullanmak yasak (Anthropic ToS, Şubat 2026; Nisan 2026'da uygulandı;
ihlal = kullanıcının hesabının banlanması). `oh-my-pi` gibi araçların yaptığı "Claude Code taklidi"
(resmi client-id + `User-Agent: claude-code/...`) tam olarak yasaklanan kalıp — OSS bir üründe riski
her kullanıcı taşır, o yüzden masada değil.

## Karar

**Tek beyin, tek loop: LangGraph.** Model katmanı OpenAI-uyumlu bir istemciyle her sağlayıcıyı bağlar
(OpenRouter · local · doğrudan API key). Claude Code SDK uygulamadan **sökülür**; abonelik yolu
tamamen düşer — Sonar kendi akıllı uygulaması olarak durur, beynini bir dış istemciden ödünç almaz.

```
┌ UI / API ────────────────────────────────┐
│  SSE taksonomisi · MessagePart registry  │
├ Agent katmanı ───────────────────────────┤
│  chat = LangGraph ReAct                  │
│  reçeteler = deterministik StateGraph    │
├ Model katmanı (tek istemci) ─────────────┤
│  OpenRouter · API key · local            │
├ Tool çekirdeği (LLM'den habersiz) ───────┤
│  13 deep tool · analytics · store · market plugin'leri
└──────────────────────────────────────────┘
```

**Sonuç (bilinçli kabul):** Claude/ChatGPT aboneliğiyle "bedava" çalışma özelliği yok; chat için bir
OpenRouter key'i ya da local model gerekir.

## Model katmanı

Tek konfigürasyon yüzeyi:

```
SONAR_MODEL     = "<provider>:<model>"     # zorunlu değil; varsayılan aşağıda
SONAR_BASE_URL  = <opsiyonel override>     # local / gateway
SONAR_API_KEY   = <opsiyonel override>     # provider'ın kendi env'i de kabul
```

| provider | model örneği | endpoint | key |
|---|---|---|---|
| `local` **(varsayılan)** | `qwen3-14b-q4` | `http://localhost:8080/v1` (llama-server) | yok |
| `openrouter` | `anthropic/claude-sonnet-4.6` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `anthropic` | `claude-sonnet-5` | resmi | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-5` | resmi | `OPENAI_API_KEY` |

**Varsayılan local:** hiçbir env değişkeni verilmeden `uv run sonar` çalışır ve local modeli kullanır —
key yok, ücret yok, veri dışarı çıkmaz. Ön koşul: makinede `llama-server` ayakta (aşağıdaki komut).
Ayakta değilse chat açık bir `error` event'i döner ("local model çalışmıyor: llama-server'ı başlat ya da
`SONAR_MODEL=openrouter:...` ver") — sessiz düşme yok, sessiz buluta kaçış da yok.

`openrouter` ve `local` OpenAI-uyumlu olduğu için **tek istemci** (`langchain-openai`) ikisini de
sürer — aralarındaki fark yalnız `base_url`. Yeni bir gateway eklemek = tablo satırı, kod değil.

**Zorunlu yetenek: tool-calling.** Sağlayıcı/model bunu veremiyorsa model katmanı `Unsupported`
döndürür ve o model listelenmez. "Tool'suz çalışan sağlayıcı" kabul edilmez.

## Local runtime (varsayılan yol)

- **Çalıştırıcı:** `llama.cpp` / `llama-server` — OpenAI-uyumlu endpoint verir; ayrıca `--jinja` +
  grammar zorlamasıyla tool çağrısını **yapısal olarak garanti** edebilir (küçük model bocalarsa asıl
  kaldıraç bu, ekstra model değil).
- **Model:** **Qwen3 14B Q4_K_M** (~9 GB; RTX 5070 12 GB'a 8–16k context ile sığar). Tool-calling'de
  bilinen güçlü aday.
- **Çalıştırma:**
  ```bash
  llama-server -m qwen3-14b-q4_k_m.gguf --jinja -c 16384 -ngl 99 --port 8080
  ```
- **Kabul kriteri (5 vaka, log'daki `tool →` satırlarından ölçülür):** tek ticker → 1 doğru çağrı ·
  çoklu ticker → her biri için ayrı çağrı · bilinmeyen sembol → uydurmadan hata anlatısı · kapsam dışı
  soru → tool'a gitmeden dürüst ret · sohbet sorusu → gereksiz tool çağırmama.
- **Geçemezse:** önce grammar zorlaması denenir; o da yetmezse local "deneysel" etiketine düşer ve
  varsayılan OpenRouter olur (ADR-0002'deki "local ertelendi" kararı bu ölçümle güncellenir).

**Opsiyon (ölçüme bağlı, şimdi yazılmaz):** tool seçimi bocalarsa döngünün iki işini ayır —
*dispatch* (hangi tool + argüman) küçük ve uzmanlaşmış bir modele ([Needle](https://github.com/cactus-compute/needle),
26M, MIT; girdi = soru + JSON tool tanımları, çıktı = `{tool, args}`), *sentez* (anlatı) büyük modele.
Bedeli: ReAct'in çok-adımlılığı (sonuca bakıp ikinci tool'u çağırma) kaybolur; dispatch tek-atışlık olur.
**Tetik:** Qwen3 14B kabul kriterini geçemezse değerlendirilir.

## Settings ekranı (v1)

Local kurulumu **kullanıcı yapar**, Sonar yol gösterir: Settings panelinde endpoint durumu
(bağlı / bağlı değil), seçili model, "bağlantıyı test et" butonu ve llama-server'ı çalıştıran komut
(kopyalanabilir). Bağlı değilse chat'teki `error` event'i de aynı yönlendirmeyi verir.

**Non-goal (şimdilik):** llama-server'ı Sonar'ın subprocess olarak başlatması, GGUF indirmesi, VRAM'e
göre `-ngl` seçmesi. Bu paketleme işidir (M6) — OS/GPU başına binâri dağıtımı gerektirir.

## Model seçimi: finans-FT model kullanmıyoruz

Fin-R1 gibi finansa fine-tune edilmiş modeller (Qwen2.5-7B tabanlı, FinQA/ConvFinQA'da güçlü) bizim
ihtiyacımızı çözmüyor: ADR-0003 gereği **sayıyı model hesaplamıyor, tool hesaplıyor**. Modelden
istediğimiz iki şey var — güvenilir tool-calling ve düzgün Türkçe anlatı. Finansal CoT fine-tune'u tam
da modelden aldığımız işte (tablo muhakemesi) iyileşiyor, buna karşılık function-calling ve Türkçe
üretim tipik olarak geriliyor. Takas aleyhimize → **genel-amaçlı, tool-calling'i güçlü model.**

Finans-özel küçük modellerin yeri **beyin değil, tool**: M2'de haber duygu analizi gibi dar görevler için
(FinBERT ailesi, ~110M) tool katmanında değerlendirilir; LLM'e dokunmaz.

## Sökülecekler

- `sonar/agent/claude_code.py` (SDK adapter)
- `events.map_sdk_message` + SDK'ya bağlı testler
- `config.PROVIDER` / `SONAR_PROVIDER` dallanması (`api/app.py` tek streamer'a döner)
- bağımlılıklar: `claude-agent-sdk`

## Katman sınırının testi

`sonar/api/`, `sonar/tools/`, `sonar/domain/`, `sonar/store/`, `sonar/market/` altında **hiçbir**
provider ithali olmayacak: `langchain*`, `langgraph`, `openai`, `anthropic`, `claude_agent_sdk`.
Import taraması yapan bir test bunu koruma altına alır — katmanlamanın laftan ibaret olmadığının kanıtı.

## Test planı

1. **Model katmanı (unit, ağsız):** `SONAR_MODEL=openrouter:...` → OpenRouter base_url'lı istemci ·
   `local:...` → `SONAR_BASE_URL`/varsayılan localhost · bilinmeyen provider → net hata.
2. **Katman sınırı (unit):** yukarıdaki import taraması.
3. **Chat akışı (mevcut):** `map_lc_event` testleri korunur; `map_sdk_message` testleri silinir.
4. **Canlı (manuel):** OpenRouter ile 5 vakalık tool testi; ardından local ile aynı 5 vaka → karşılaştır.

## Non-goals

- Uygulama içinde Claude Code SDK / Agent SDK.
- Abonelik OAuth token'ını kendi loop'umuzda kullanmak (ToS, ban riski).
- MCP server ("harici beyin" kapısı) — Sonar kendi akıllı uygulaması; dış istemciye beyin ödünç vermek
  ürünün yönü değil. (ADR-0007'deki MCP cümlesi buna göre güncellenecek.)
- `deepagents` harness'ı (ADR-0007'de gerekçesiyle reddedildi).
- Finansa fine-tune edilmiş beyin modeli (yukarıda gerekçelendirildi).
- Chat'in çok-adımlılığından vazgeçmek (Needle yalnız ölçüm tetiklerse ve ayrı tartışmayla gelir).

## Geri dönüş

SDK yolu git geçmişinde duruyor (`ca55072`). OpenRouter/local yolları çalışmazsa tek commit geri alınır.
