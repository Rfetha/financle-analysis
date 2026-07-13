# 0002 — Model katmanı: OpenAI-uyumlu tek istemci; varsayılan local, abonelik yolu yok

Sonar herhangi bir anda **tek** model kullanır; kullanıcı seçer. Model katmanı (`sonar/agent/model.py`)
env'den bir chat model üretir, üst katmanlar sağlayıcıdan habersizdir:

| provider | endpoint | key |
|---|---|---|
| `local` **(varsayılan)** | `http://localhost:8080/v1` (llama-server) | yok |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `anthropic` · `openai` · … | resmi | ilgili key |

`local` ve `openrouter` OpenAI-uyumlu olduğu için tek istemciden geçer (fark: `base_url`).
`SONAR_BASE_URL` ile Ollama/LM Studio/gateway'e yönlenir. **Zorunlu yetenek: tool-calling.**

## Abonelik OAuth reddedildi (2026-07-13'te güncellendi)

Önceki karar "abonelik OAuth öncelikli" idi. Gerçekle çarpıştı:

- **Anthropic ToS (Şubat 2026, Nisan'da uygulandı):** abonelik OAuth token'ının başka bir üründe
  kullanımı yasak → ihlal = **kullanıcının** hesabının banlanması. `oh-my-pi` gibi araçların yaptığı
  "Claude Code taklidi" (resmi client-id + `User-Agent: claude-code/...`) tam olarak bu maddedir; OSS
  bir üründe riski her kullanıcı taşır.
- **ToS-uyumlu tek yol** Claude Code SDK'yı sürmekti (M1'de yazıldı, çalıştı — `ca55072`). Reddedildi:
  uygulamanın çekirdek akışı dış bir binary'nin davranışına bağlanıyor (versiyon kayması), fatura
  modeli sağlayıcının elinde (Haziran 2026'da ayrı kredi havuzu denendi, geri çekildi), ve chat'te
  ikinci bir agent loop'u bakımı gerekiyor.

**Sonuç:** Sonar beynini dış istemciden ödünç almaz. Bedeli bilinçli kabul edildi — chat için
OpenRouter key'i ya da local model gerekir.

## Consequences
- Sağlayıcı eklemek = model katmanında bir satır; `api/`, `tools/`, `domain/`, `store/`, `market/`
  değişmez (import-tarama testiyle korunuyor: `tests/test_layering.py`).
- Local varsayılan → key'siz, ücretsiz, veri makineden çıkmaz. Ön koşul: llama-server ayakta.
- Local'in geleceği **ölçüme bağlı**: Qwen3 14B Q4 beş-vakalık tool-calling testini geçemezse
  varsayılan OpenRouter'a döner (spec: `docs/superpowers/specs/2026-07-13-model-layer-and-mcp-door-design.md`).
