import logging

from langchain_core.messages import AIMessage, HumanMessage

from assessor_ai.graph.builder import fluxo_agentes
from assessor_ai.schemas.models import ChatMessage, Role
from assessor_ai.tools.infra.postgres import reset_current_user, set_current_user

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


def _extrair_resposta(estado_final: dict) -> str | None:
    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.text
    return None


async def executar(
    mensagem: ChatMessage, session_id: str, perfil_usuario: str, user_id: str
) -> str | None:
    estado_inicial = {
        "messages": [_PARA_LANGCHAIN[mensagem.role](content=mensagem.content)],
        "agentes_chamados": [],
        "perfil_usuario": perfil_usuario,
    }

    # As tools síncronas de Postgres rodam em thread do executor do LangChain, que copia o
    # contextvar da task atual — por isso o `set_current_user` aqui continua valendo lá dentro.
    token = set_current_user(user_id)
    try:
        grafo = await fluxo_agentes()
        estado_final = await grafo.ainvoke(
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
