"""Chat agent = LangGraph create_react_agent (ADR-0006/0007): dinamik tool seçimi."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from sonar.agent import events

SYSTEM = (
    "Sen Sonar'sın: OSS, provider-bağımsız bir ABD borsası araştırma asistanı. "
    "Fiyat/piyasa verisi gerektiğinde tool'ları kullan; sayıları kendin uydurma, "
    "tool sonucuna dayan. Kısa, net, Türkçe yanıtla."
)


def build_agent(*, model, tools, checkpointer=None):
    # ponytail: MemorySaver = tek-oturum thread memory. Restart'lar arası kalıcılık
    # gerekirse SqliteSaver'a (aynı DB, ADR-0004) yükselt.
    return create_react_agent(
        model, tools, prompt=SYSTEM, checkpointer=checkpointer or MemorySaver()
    )


def make_streamer(*, registry, cache, ttl):
    """(message, thread_id) -> Sonar SSE event akışı (API-key yolu, ADR-0002)."""
    agent = None

    async def stream(message: str, thread_id: str):
        nonlocal agent
        if agent is None:  # model init ilk istekte — API key yoksa hata SSE error'a düşsün
            from sonar.agent.model import default_model
            from sonar.agent.tools import make_quote_tool

            tool = make_quote_tool(registry=registry, cache=cache, ttl=ttl)
            agent = build_agent(model=default_model(), tools=[tool])
        async for ev in agent.astream_events(
            {"messages": [("user", message)]},
            config={"configurable": {"thread_id": thread_id}},
            version="v2",
        ):
            for event in events.map_lc_event(ev):
                yield event

    return stream
