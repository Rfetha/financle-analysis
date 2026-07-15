"""DeepAnalysis (UC1) — deterministik reçete (ADR-0007). ReAct YOK, döngü YOK.

gather : LLM içermez; deep tool'ları paralel çağırır. Bir kaynak düşerse rapor düşmez —
         o bölüm {"unavailable": sebep} olur, sentez "bu veri yok" der (sessiz boşluk yasak).
synthesize : TEK LLM çağrısı. Aritmetik yasak — bütün sayılar gather çıktısında hazır (ADR-0003).

LangGraph StateGraph kullanmıyoruz: iki düğüm, dallanma yok, döngü yok → graf makinesi burada
sıfır bilgi saklardı (shallow). asyncio.gather + tek çağrı aynı işi yapıyor. Dallanma gerekirse
(Faz B'de big_players koşullu olsaydı) StateGraph'a yükselt.
"""

import asyncio
import json
from typing import Callable

from loguru import logger

from sonar.agent import events
from sonar.agent.events import _text_of
from sonar.market.base import Unsupported
from sonar.tools.fundamentals import get_fundamentals
from sonar.tools.holders import get_institutional_holders
from sonar.tools.insiders import get_insider_trades
from sonar.tools.macro import get_macro_snapshot
from sonar.tools.news import get_news
from sonar.tools.peers import get_peers
from sonar.tools.short_interest import get_short_interest
from sonar.tools.technicals import get_technicals
from sonar import config

SYNTHESIS_PROMPT = """Sen Sonar'sın; bir ABD borsası araştırma asistanı.

Aşağıda {ticker} için TOPLANMIŞ ve HESAPLANMIŞ veri var. Görevin YALNIZCA sentez:

- Hiçbir aritmetik yapma. Fark, oran, yüzde HESAPLAMA — hepsi zaten aşağıda.
- Veride olmayan bir sayı UYDURMA. Bir bölüm "unavailable" ise "bu veri şu an yok" de, tahmin etme.
- Top-down yaz ve şu sırayı koru:
  1. MAKRO — ortam bu hisseye lehte mi? (faiz, TÜFE, getiri eğrisi, VIX, dolar)
  2. MİKRO — şirketin durumu (gelir, büyüme, marj) + rakiplerle konumu
  3. TEKNİK — trend, momentum, destek/direnç, hacim
  4. HABER — son başlıklar ne söylüyor
  5. BÜYÜK OYUNCULAR — kurumlar ne yaptı (13F Δ: yeni giriş/çıkış/artırma/azaltma), yöneticiler
     ne yaptı (Form 4 cluster), toplam short. ZORUNLU: her Big Players cümlesinde
     provenance_note'taki gecikmeyi belirt (ör. "13F, 45 gün gecikmeli"); gecikmeli veriyi
     güncel gibi sunma; short/swap görünmediğini saklama.
  6. SENTEZ — dört katman birbirini destekliyor mu, çelişiyor mu? Ana risk ne?
- Yatırım tavsiyesi verme; gözlem ve risk yaz.
- Türkçe, kısa, net. Her iddianın arkasında yukarıdaki bir sayı olsun.

VERİ:
{data}
"""

# Bölüm adı → o bölümü hesaplayan fonksiyon. TEK kaynak: hem gather hem analyze bunu kullanır
# (ayrı listeler tutulsaydı biri güncellenip diğeri unutulurdu).
def _section_fns(ticker: str, ctx: dict) -> dict[str, Callable[[], dict]]:
    # Why: ctx registry/cache/conn taşır ama macro/fundamentals/... conn kabul etmez —
    # bu yüzden **ctx yerine registry/cache açıkça geçilir (big_players conn'u ayrı okur).
    market_ctx = {"registry": ctx["registry"], "cache": ctx["cache"]}
    return {
        "macro": lambda: get_macro_snapshot(**market_ctx, ttl=config.MACRO_TTL_SECONDS),
        "fundamentals": lambda: get_fundamentals(
            ticker, **market_ctx, ttl=config.FUNDAMENTALS_TTL_SECONDS
        ),
        "technicals": lambda: get_technicals(ticker, **market_ctx, ttl=config.OHLCV_TTL_SECONDS),
        "news": lambda: get_news(ticker, **market_ctx, ttl=config.NEWS_TTL_SECONDS),
        "peers": lambda: get_peers(ticker, **market_ctx, ttl=config.PEERS_TTL_SECONDS),
        "big_players": lambda: {
            "holders": get_institutional_holders(
                ticker, conn=ctx["conn"], cache=ctx["cache"], ttl=config.HOLDERS_TTL_SECONDS
            ),
            "insiders": get_insider_trades(
                ticker,
                registry=ctx["registry"],
                cache=ctx["cache"],
                ttl=config.INSIDERS_TTL_SECONDS,
            ),
            "short": get_short_interest(
                ticker, registry=ctx["registry"], cache=ctx["cache"], ttl=config.SHORT_TTL_SECONDS
            ),
        },
    }


SECTIONS = ("macro", "fundamentals", "technicals", "news", "peers", "big_players")


def _run(ticker: str, name: str, fn: Callable[[], dict]) -> dict:
    """Tek bölüm. Kaynak düşerse rapor DÜŞMEZ — bölüm 'unavailable' olur, hata loglanır."""
    try:
        return fn()
    except Unsupported as e:
        logger.info("analiz[{}] {} desteklenmiyor: {}", ticker, name, e)
        return {"unavailable": str(e)}
    except Exception as e:  # noqa: BLE001
        # Why: tek bir dış kaynağın çökmesi (EDGAR 500, RSS timeout) raporun tamamını
        # düşürmemeli. Hata YUTULMUYOR — loglanıyor ve çıktıda görünür kalıyor.
        logger.warning("analiz[{}] {} düştü: {}", ticker, name, e)
        return {"unavailable": f"{type(e).__name__}: {e}"}


def gather(ticker: str, *, registry, cache, conn=None) -> dict:
    """Deep tool'ları çağırır (senkron, sıralı). LLM yok."""
    fns = _section_fns(ticker, {"registry": registry, "cache": cache, "conn": conn})
    return {name: _run(ticker, name, fns[name]) for name in SECTIONS}


def make_analyzer(*, registry, cache, conn=None, model_factory: Callable | None = None):
    """(ticker) -> Sonar SSE event akışı. Model ilk istekte kurulur (hata SSE error'a düşsün)."""

    async def analyze(ticker: str):
        loop = asyncio.get_running_loop()
        fns = _section_fns(ticker, {"registry": registry, "cache": cache, "conn": conn})

        # Bölümler PARALEL koşar; her biri bitince adım event'i akar (sıra korunur).
        tasks = {
            name: loop.run_in_executor(None, _run, ticker, name, fns[name]) for name in SECTIONS
        }
        data: dict[str, dict] = {}
        for name in SECTIONS:
            data[name] = await tasks[name]
            yield events.ANALYSIS_STEP, {
                "section": name,
                "ok": "unavailable" not in data[name],
            }

        yield events.CHART, {"ticker": ticker.upper(), "range": "6mo", "interval": "1d"}

        model = (model_factory or _default_model_factory)()
        prompt = SYNTHESIS_PROMPT.format(
            ticker=ticker.upper(), data=json.dumps(data, ensure_ascii=False, indent=2)
        )
        async for chunk in model.astream(prompt):
            text = _text_of(getattr(chunk, "content", ""))
            if text:
                yield events.TEXT_DELTA, {"delta": text}

    return analyze


def _default_model_factory():
    from sonar.agent.model import default_model

    return default_model()
