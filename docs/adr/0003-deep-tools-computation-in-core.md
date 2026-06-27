# 0003 — Derin tool'lar: hesap çekirdekte, LLM yalnız sentez

Tool'lar ham veri değil, **hesaplanmış/normalize edilmiş yapılandırılmış sonuç** döner
(RSI, P&L, korelasyon, kurumsal Δ — hepsi Python `analytics` katmanında hesaplanır).
LLM'e sayısal/analitik yargı **bırakılmaz**; modelin işi yalnız sentez ve anlatı.

Sebep: LLM aritmetik ve tutarlı hesapta güvenilmez. Tüm sayı işini deterministik
Python'a almak halüsinasyonu düşürür ve UC1/UC7 doğruluk kriterini (sayılar kaynakla
doğrulanabilir) tutturur. Bu, global "deep module" + "analytics çekirdekte" ilkesinin
proje-özel uygulamasıdır.
