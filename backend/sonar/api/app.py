from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sonar import config
from sonar.store.db import connect
from sonar.store.cache import Cache
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.market.base import UnknownSymbol
from sonar.tools.quote import get_quote
from sonar.agent import events


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


def _default_registry() -> MarketRegistry:
    reg = MarketRegistry()
    reg.register(USMarketPlugin())
    return reg


def create_app(
    registry: MarketRegistry | None = None,
    cache: Cache | None = None,
    agent=None,
) -> FastAPI:
    app = FastAPI(title="Sonar")
    registry = registry or _default_registry()
    cache = cache or Cache(connect(config.DB_PATH))

    def _get_agent():
        # Agent'ı lazy kur: LLM/model init ilk chat isteğinde (API key gerekir).
        nonlocal agent
        if agent is None:
            from sonar.agent.graph import build_agent
            from sonar.agent.model import default_model
            from sonar.agent.tools import make_quote_tool

            tool = make_quote_tool(registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS)
            agent = build_agent(model=default_model(), tools=[tool])
        return agent

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
            config_ = {"configurable": {"thread_id": req.thread_id or "default"}}
            try:
                agent_ = _get_agent()
                async for ev in agent_.astream_events(
                    {"messages": [("user", req.message)]}, config=config_, version="v2"
                ):
                    for etype, data in events.map_lc_event(ev):
                        yield events.sse(etype, data)
            except Exception as e:  # provider/key/tool hatası → tek error event, sessiz düşme yok
                yield events.sse(events.ERROR, {"message": str(e)})
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")

    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
