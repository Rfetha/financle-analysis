"""Chat agent = LangGraph create_react_agent (ADR-0006/0007): dinamik tool seçimi."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from loguru import logger

from sonar.agent import events

SYSTEM = (
    "Adın Sonar; bir ABD borsası araştırma asistanısın. "
    "Fiyat/piyasa verisi gerektiğinde tool'ları kullan; sayıları kendin uydurma, "
    "tool sonucuna dayan. Hesap yapma (fark/oran/yüzde) — hesaplanmış değer tool'dan gelir, "
    "yoksa 'elimde yok' de. Hangi model/altyapı üzerinde çalıştığını anlatma. "
    "Kısa, net, Türkçe yanıtla."
)


def build_agent(*, model, tools, checkpointer=None):
    # ponytail: MemorySaver = tek-oturum thread memory. Restart'lar arası kalıcılık
    # gerekirse SqliteSaver'a (aynı DB, ADR-0004) yükselt.
    return create_react_agent(
        model, tools, prompt=SYSTEM, checkpointer=checkpointer or MemorySaver()
    )


def make_streamer(*, registry, cache, conn=None):
    """(message, thread_id) -> Sonar SSE event akışı. Model katmanı env'den seçer (ADR-0002)."""
    agent = None

    async def stream(message: str, thread_id: str):
        nonlocal agent
        if agent is None:  # model init ilk istekte — model/key hatası SSE error'a düşsün
            from sonar.agent.model import default_model
            from sonar.agent.tools import make_tools

            model = default_model()
            logger.info("agent kuruldu — model: {}", getattr(model, "model_name", model))
            agent = build_agent(
                model=model, tools=make_tools(registry=registry, cache=cache, conn=conn)
            )
        async for ev in agent.astream_events(
            {"messages": [("user", message)]},
            config={"configurable": {"thread_id": thread_id}},
            version="v2",
        ):
            for event in events.map_lc_event(ev):
                yield event

    return stream
