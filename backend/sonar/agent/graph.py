"""Chat agent = LangGraph create_react_agent (ADR-0006/0007): dinamik tool seçimi."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

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
