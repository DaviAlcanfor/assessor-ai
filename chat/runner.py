import logging
import warnings

from langchain_core.messages import AIMessage, HumanMessage

from chat.models import ChatMessage, Role
from graph.builder import fluxo_agentes

warnings.filterwarnings("ignore", message="Deserializing unregistered type")
logging.getLogger("langgraph").setLevel(logging.ERROR)


_PARA_LANGCHAIN = {
    Role.HUMAN: HumanMessage,
    Role.AI:    AIMessage,
}


def _extrair_resposta(estado_final: dict) -> str | None:
    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.content
    return None


def executar(mensagem: ChatMessage, session_id: str, perfil_usuario: str) -> str | None:
    estado_inicial = {
        "messages":         [_PARA_LANGCHAIN[mensagem.role](content=mensagem.content)],
        "agentes_chamados": [],
        "perfil_usuario":   perfil_usuario,
    }

    estado_final = fluxo_agentes.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": session_id}},
    )

    return _extrair_resposta(estado_final)


__all__ = ["executar"]
