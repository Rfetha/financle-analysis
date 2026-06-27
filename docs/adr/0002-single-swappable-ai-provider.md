# 0002 — Tek sabit, kullanıcı-seçimli AI sağlayıcı; abonelik OAuth öncelikli

Sonar herhangi bir anda **tek** model+provider kullanır (görev başına model karışımı
yok); provider'ı kullanıcı seçer/değiştirir. Öncelik sırası: **(1) abonelik OAuth** —
"Sign in with ChatGPT" (Codex/OpenAI) **veya** Claude aboneliği; **(2) API key**
(Anthropic/OpenAI); **(3) ileride** OpenRouter + local model. Soyutlama PydanticAI;
provider değiştirmek = config değişikliği.

## Consequences
- **ChatGPT/Codex OAuth** uygulamaya doğrudan gömülür (resmi "Sign in with ChatGPT";
  üçüncü-parti araçlarca destekleniyor) → in-app chat çalışır.
- **Claude aboneliği** kendi agent loop'umuzda kullanılamaz (Anthropic Şubat 2026 ToS,
  ban riski). Seçilirse beyin **Claude Code / Agent SDK** üzerinden sürülür — ToS-uyumlu.
  Kullanıcıya tek config gibi görünür, fark arkada.
- **API key** her zaman en basit yol; PydanticAI doğrudan çalıştırır.
- Local model ertelendi (kalite yetersiz — kullanıcı kararı).
