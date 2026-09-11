import logging
from typing import cast

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from assessor_ai.graph.builder import fluxo_agentes
from assessor_ai.graph.state import Estado, SaidaGrafo
from assessor_ai.identifiers import (
    ChatID,
    UserID,
    reset_usuario_atual,
    set_usuario_atual,
)
from assessor_ai.infra.postgres import reset_current_user, set_current_user
from assessor_ai.schemas.models import ChatMessage, Role

# O aviso "Deserializing unregistered type" sai por `logger.warning` do serde do langgraph, não
# pelo módulo `warnings` — filtrar em `warnings.filterwarnings` era no-op. Silenciado no logger do
# módulo que emite, e não no logger `langgraph` inteiro, pra não engolir o resto.
# ponytail: o fix de raiz é passar `allowed_msgpack_modules` no serde do checkpointer, mas a lista
# liga o modo estrito (bloqueia o que não estiver nela) — trocar só com teste ponta a ponta.
logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)


_PARA_LANGCHAIN = {
    Role.HUMAN: HumanMessage,
    Role.AI: AIMessage,
}


def _extrair_resposta(estado_final: SaidaGrafo) -> str | None:
    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.text
    return None


async def executar(
    mensagem: ChatMessage, session_id: ChatID, perfil_usuario: str, user_id: UserID
) -> str | None:
    estado_inicial: Estado = {
        "messages": [_PARA_LANGCHAIN[mensagem.role](content=mensagem.content)],
        "agentes_chamados": [],
        "perfil_usuario": perfil_usuario,
    }

    config: RunnableConfig = {
        "configurable": {"thread_id": session_id},
        "tags": ["chat"],
        "metadata": {"user_id": user_id, "session_id": session_id},
    }

    # As tools síncronas de Postgres/Mongo/Qdrant rodam em thread do executor do LangChain, que
    # copia o contextvar da task atual — por isso os `set_*` aqui continuam valendo lá dentro.
    token = set_current_user(user_id)
    token_usuario = set_usuario_atual(user_id)
    try:
        grafo = await fluxo_agentes.get()
        # ainvoke() devolve tipo fraco no stub do langgraph mesmo com output_schema declarado.
        estado_final = cast(SaidaGrafo, await grafo.ainvoke(estado_inicial, config=config))
    finally:
        reset_current_user(token)
        reset_usuario_atual(token_usuario)

    return _extrair_resposta(estado_final)


__all__ = ["executar"]
