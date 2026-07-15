import asyncio
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from sonar import config
from sonar.store.db import connect
from sonar.store.cache import Cache
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.market.base import UnknownSymbol
from sonar.tools.quote import get_quote
from sonar.tools.ohlcv import get_ohlcv
from sonar.agent import events


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class AnalyzeRequest(BaseModel):
    ticker: str


def _default_registry() -> MarketRegistry:
    from sonar.market.us.prices import make_price_source

    reg = MarketRegistry()
    reg.register(USMarketPlugin(make_price_source()))
    return reg


def create_app(
    registry: MarketRegistry | None = None,
    cache: Cache | None = None,
    streamer=None,
    analyzer=None,
    conn=None,
) -> FastAPI:
    registry = registry or _default_registry()
    conn = conn or connect(config.DB_PATH)
    cache = cache or Cache(conn)

    _state: dict = {"ingester": None}  # lifespan yazar, status endpoint okur
    _ingest_tasks: set[asyncio.Task] = set()  # Why: GC referansı kaybetmesin (Python gotcha)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 13F arka plan ingestion — açılışta (spec §7: sessiz değil, /api/ingest/status'tan görünür).
        if not os.environ.get("SONAR_SKIP_INGEST"):  # testler ve CI atlar
            from sonar.market.sources.http import HttpClient
            from sonar.market.us.cusip import CusipMap
            from sonar.market.us.edgar import TICKERS_URL
            from sonar.store.holdings_repo import HoldingsRepo
            from sonar.store.ingest import Ingester

            ingest_conn = conn or connect(config.DB_PATH)
            http = HttpClient(f"Sonar/0.1 ({os.environ.get('SONAR_CONTACT', 'sonar@localhost')})")
            loop = asyncio.get_running_loop()
            tickers = await loop.run_in_executor(None, http.get_json, TICKERS_URL)
            ingester = Ingester(HoldingsRepo(ingest_conn), CusipMap(ingest_conn), http, tickers)
            _state["ingester"] = ingester
            task = asyncio.create_task(ingester.run())  # fire-and-forget; hata state'te görünür
            _ingest_tasks.add(task)
            task.add_done_callback(_ingest_tasks.discard)
        yield

    app = FastAPI(title="Sonar", lifespan=lifespan)

    @app.get("/api/ingest/status")
    def ingest_status() -> dict:
        ingester = _state["ingester"]
        if ingester is None:
            return {"status": "idle", "progress": 0.0, "quarter": "", "message": ""}
        s = ingester.state
        return {"status": s.status, "progress": s.progress, "quarter": s.quarter, "message": s.message}

    def _get_streamer():
        # Agent'ı lazy kur: model init ilk chat isteğinde (model katmanı env'den seçer).
        nonlocal streamer
        if streamer is None:
            from sonar.agent.graph import make_streamer

            streamer = make_streamer(registry=registry, cache=cache, conn=conn)
        return streamer

    def _get_analyzer():
        nonlocal analyzer
        if analyzer is None:
            from sonar.agent.recipes.deep_analysis import make_analyzer

            analyzer = lambda: make_analyzer(registry=registry, cache=cache, conn=conn)  # noqa: E731
        return analyzer()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/quote/{ticker}")
    def quote(ticker: str) -> dict:
        try:
            return get_quote(ticker, registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS)
        except UnknownSymbol:
            raise HTTPException(status_code=404, detail=f"Sembol bulunamadı: {ticker.upper()}")

    @app.post("/api/chat")
    async def chat(req: ChatRequest) -> StreamingResponse:
        async def stream():
            thread = req.thread_id or "default"
            started = time.perf_counter()
            logger.info("chat[{}] ← {!r}", thread, req.message)
            deltas = 0
            try:
                async for etype, data in _get_streamer()(req.message, thread):
                    if etype == events.TEXT_DELTA:
                        deltas += 1  # tek tek loglamak gürültü; sonda sayısı yazılır
                    elif etype == events.TOOL_CALL:
                        logger.info("chat[{}] tool → {}({})", thread, data["name"], data["input"])
                    elif etype == events.TOOL_RESULT:
                        logger.info("chat[{}] tool ← {} {:.200}", thread, data["name"], data["output"])
                    elif etype == events.ERROR:
                        logger.error("chat[{}] agent hatası: {}", thread, data["message"])
                    yield events.sse(etype, data)
            except Exception as e:  # model/auth/tool hatası → tek error event, sessiz düşme yok
                from sonar.agent.model import explain

                logger.exception("chat[{}] akış çöktü", thread)
                yield events.sse(events.ERROR, {"message": explain(e)})
            logger.info(
                "chat[{}] ✓ {} text-delta, {:.1f}s", thread, deltas, time.perf_counter() - started
            )
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/ohlcv/{ticker}")
    def ohlcv(ticker: str, range: str = "6mo", interval: str = "1d") -> dict:
        try:
            return get_ohlcv(
                ticker, range, interval,
                registry=registry, cache=cache, ttl=config.OHLCV_TTL_SECONDS,
            )
        except UnknownSymbol:
            raise HTTPException(status_code=404, detail=f"Sembol bulunamadı: {ticker.upper()}")

    @app.post("/api/analyze")
    async def analyze(req: AnalyzeRequest) -> StreamingResponse:
        async def stream():
            started = time.perf_counter()
            logger.info("analiz[{}] başladı", req.ticker)
            try:
                async for etype, data in _get_analyzer()(req.ticker):
                    if etype == events.ANALYSIS_STEP:
                        logger.info("analiz[{}] {} {}", req.ticker, data["section"],
                                    "✓" if data["ok"] else "✗")
                    yield events.sse(etype, data)
            except Exception as e:  # model/tool hatası → tek error event, sessiz düşme yok
                from sonar.agent.model import explain

                logger.exception("analiz[{}] akış çöktü", req.ticker)
                yield events.sse(events.ERROR, {"message": explain(e)})
            logger.info("analiz[{}] ✓ {:.1f}s", req.ticker, time.perf_counter() - started)
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/stream/quotes")
    async def stream_quotes(tickers: str) -> StreamingResponse:
        from sonar.api.quotes import quote_stream

        symbols = [t.strip() for t in tickers.split(",") if t.strip()]

        async def stream():
            try:
                async for etype, data in quote_stream(symbols, registry=registry, cache=cache):
                    yield events.sse(etype, data)
            except asyncio.CancelledError:
                raise  # Why: istemci bağlantıyı kapattı — yutma, propagate et (CLAUDE.md §5)
            except Exception as e:  # model/tool hatası → tek error event, sessiz düşme yok
                logger.exception("quote-stream akış çöktü")
                yield events.sse(events.ERROR, {"message": str(e)})
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")

    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
