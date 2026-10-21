import re

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.agents import router_app
from app.graph.names import ROTEADOR
from app.graph.nodes.contexto import mensagens_com_contexto, responder
from app.graph.prompts.loader import load_sections
from app.graph.state import Estado, Route, RouterUpdate
from app.infra.llm import jev
from app.infra.logging import Logging
from app.telemetry import medir_node
from app.telemetry.metrics import ROUTER_DECISIONS

log = Logging.get_logger(__name__)

_PROMPTS = load_sections("router")

_NENHUMA_ROTA = "nenhum"

# Opções do JeV (rota → descrição); "nenhum" devolve a vez pro LLM, que escreve a resposta.
DESCRICAO_ROTA: dict[str, str] = {
    Route.FINANCEIRO: "gastos, receitas, dívidas, orçamento, metas, saldo, investimentos",
    Route.AGENDA:     "compromissos, eventos, lembretes, tarefas, horários, conflitos",
    Route.FAQ: (
        "dúvidas sobre o Assessor.AI: regras, políticas, termos, privacidade, segurança, "
        "contato/suporte e comportamento do sistema"
    ),
    _NENHUMA_ROTA: (
        "saudação, conversa fiada, assunto fora de finanças/agenda, ou resposta curta que só faz "
        "sentido com o histórico da conversa"
    ),
}


def _extrair_rota(texto: str) -> Route:

    match = re.search(r"ROUTE=(\w+)", texto)
    if not match:
        return Route.FIM
    
    try:
        return Route(match.group(1))
    except ValueError:
        return Route.FIM


def _extrair_pergunta(texto: str) -> str:

    match = re.search(r"PERGUNTA_ORIGINAL=(.+)", texto)
    if not match:
        return ""

    return match.group(1).strip()


async def _rotear_com_jev(estado: Estado) -> tuple[Route, str] | None:
    """Rota e pergunta original quando o JeV reconhece o domínio olhando só a última mensagem;
    None quando o LLM precisa entrar (escrever saudação/fora de escopo, ou follow-up que só faz
    sentido com o histórico) ou quando o JeV falha."""

    pergunta = next(m.text for m in reversed(estado["messages"]) if isinstance(m, HumanMessage))
    try:
        escolha = await jev.escolher("roteador", pergunta, _PROMPTS["rota_jev"], DESCRICAO_ROTA)
    except Exception as e:
        log.warning("Roteador JeV falhou, usando o LLM: %s", e)
        return None

    return None if escolha == _NENHUMA_ROTA else (Route(escolha), pergunta)


@medir_node(ROTEADOR)
async def no_roteador(estado: Estado) -> RouterUpdate:

    if jev.disponivel() and (decidida := await _rotear_com_jev(estado)):
        rota, pergunta = decidida
        log.debug(f"Rota escolhida pelo JeV: {rota} | pergunta: '{pergunta}'")
        ROUTER_DECISIONS.labels(route=rota.value).inc()
        return RouterUpdate(agentes_chamados=[ROTEADOR], rota=rota, pergunta_original=pergunta)

    texto = await responder(router_app, mensagens_com_contexto(estado, incluir_pergunta=False))
    rota  = _extrair_rota(texto)
    pergunta = _extrair_pergunta(texto)

    log.debug(f"Rota escolhida: {rota} | pergunta: '{pergunta}'")
    ROUTER_DECISIONS.labels(route=rota.value).inc()

    if rota is Route.FIM:
        return RouterUpdate(
            agentes_chamados=[ROTEADOR],
            rota=Route.FIM,
            pergunta_original=pergunta,
            messages=[AIMessage(content=texto)],
        )

    return RouterUpdate(
        agentes_chamados=[ROTEADOR],
        rota=rota,
        pergunta_original=pergunta,
    )