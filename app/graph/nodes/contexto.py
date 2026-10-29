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

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable

from app.graph.prompts.loader import contexto_do_turno
from app.graph.state import Estado


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


async def responder_com_evidencias(
    app: Runnable[Any, Any], mensagens: Sequence[AnyMessage]
) -> tuple[str, str]:
    """
    Roda o agente e devolve o texto da última mensagem dele e as evidências do turno: cada tool chamada,
    com os argumentos que recebeu e o que devolveu. É contra isso que o juiz confere a resposta.
    Sem nenhuma tool chamada, a própria resposta é a evidência.

    Os argumentos entram porque o retorno de uma escrita não repete o que foi gravado (o `add_transaction`
    devolve só `id` e `occurred_at`). `messages` do estado só tem Human/AI, então todo `ToolMessage` da
    saída é desta execução.
    """

    saida = await app.ainvoke({"messages": list(mensagens)})
    mensagens_saida = saida["messages"]
    conteudo = mensagens_saida[-1].content

    if not isinstance(conteudo, str):
        raise RespostaAgenteInvalida("O agente não retornou conteúdo textual.")

    args_por_chamada = {
        chamada["id"]: chamada["args"]
        for m in mensagens_saida if isinstance(m, AIMessage)
        for chamada in m.tool_calls
    }
    evidencias = "\n\n".join(
        f"{m.name}({args_por_chamada.get(m.tool_call_id, {})}) -> {m.content}"
        for m in mensagens_saida if isinstance(m, ToolMessage)
    )

    return conteudo, evidencias or conteudo


async def responder(app: Runnable[Any, Any], mensagens: Sequence[AnyMessage]) -> str:
    """Roda o agente com `mensagens` e devolve o texto da última mensagem que ele produziu."""

    resposta, _ = await responder_com_evidencias(app, mensagens)

    return resposta


__all__ = ["RespostaAgenteInvalida", "mensagens_com_contexto", "responder", "responder_com_evidencias"]
