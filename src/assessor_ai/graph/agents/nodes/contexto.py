"""
Glue entre os nós do grafo e os agentes compilados.

`mensagens_com_contexto` monta a entrada: `perfil_usuario` e `pergunta_original` vivem no Estado
do grafo, mas os agentes (`graph/agents/`) são compilados no import com system_prompt fixo — sem
isso o especialista nunca enxerga nem o perfil nem a pergunta que o roteador encaminhou.

`responder` roda o agente e devolve o texto da última mensagem — todo nó fazia
`ainvoke({"messages": ...})["messages"][-1].content` na mão.
"""

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.runnables import Runnable

from assessor_ai.graph.agents.prompts.loader import contexto_do_turno
from assessor_ai.graph.state import Estado


class RespostaAgenteInvalida(RuntimeError):
    pass


def mensagens_com_contexto(
    estado: Estado, incluir_pergunta: bool = True
) -> list[AnyMessage]:
    """
    Histórico do turno precedido de uma mensagem de sistema com data/hora atual,
    perfil do usuário e (opcionalmente) a pergunta encaminhada pelo roteador.
    """

    contexto = contexto_do_turno(
        perfil_usuario=estado.get("perfil_usuario", ""),
        pergunta_original=estado.get("pergunta_original", "") if incluir_pergunta else "",
    )

    return [SystemMessage(content=contexto), *estado["messages"]]


async def responder(app: Runnable[Any, Any], mensagens: Sequence[AnyMessage]) -> str:
    """Roda o agente com `mensagens` e devolve o texto da última mensagem que ele produziu."""

    saida = await app.ainvoke({"messages": list(mensagens)})
    conteudo = saida["messages"][-1].content

    if not isinstance(conteudo, str):
        raise RespostaAgenteInvalida("O agente não retornou conteúdo textual.")

    return conteudo


__all__ = ["RespostaAgenteInvalida", "mensagens_com_contexto", "responder"]
