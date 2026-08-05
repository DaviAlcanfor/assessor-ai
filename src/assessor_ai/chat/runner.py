import logging
import warnings

from langchain_core.messages import AIMessage, HumanMessage

from assessor_ai.chat.models import ChatMessage, Role
from assessor_ai.graph.builder import fluxo_agentes
from assessor_ai.tools.postgres.connection import reset_current_user, set_current_user

warnings.filterwarnings("ignore", message="Deserializing unregistered type")
logging.getLogger("langgraph").setLevel(logging.ERROR)


_PARA_LANGCHAIN = {
    Role.HUMAN: HumanMessage,
    Role.AI: AIMessage,
}


def _extrair_resposta(estado_final: dict) -> str | None:
    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.content
    return None


def executar(
    mensagem: ChatMessage, session_id: str, perfil_usuario: str, user_id: str
) -> str | None:
    estado_inicial = {
        "messages": [_PARA_LANGCHAIN[mensagem.role](content=mensagem.content)],
        "agentes_chamados": [],
        "perfil_usuario": perfil_usuario,
    }

    token = set_current_user(user_id)
    try:
        estado_final = fluxo_agentes.invoke(
            estado_inicial,
            config={
                "configurable": {"thread_id": session_id},
                "tags": ["chat"],
                "metadata": {"user_id": user_id, "session_id": session_id},
            },
        )
    finally:
        reset_current_user(token)

    return _extrair_resposta(estado_final)


__all__ = ["executar"]
