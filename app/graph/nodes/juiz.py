from enum import StrEnum

from app.graph.guardrail.saida import FRASE_SEGURA
from app.graph.names import JUIZ
from app.graph.prompts.loader import load_sections
from app.graph.state import Estado, JuizUpdate
from app.infra.llm import jev
from app.infra.llm.jev.schemas import PerguntaEscolha, PerguntaPredicado
from app.infra.logging import Logging
from app.infra.postgres import transacao_atual
from app.telemetry import medir_node

logger = Logging.get_logger(__name__)

_PROMPTS = load_sections("juiz")


class Veredito(StrEnum):
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"

    # Sem chave do gateway, erro, timeout ou recusa do JeV: a avaliação não aconteceu.
    INDISPONIVEL = "INDISPONIVEL"


class Grounding(StrEnum):
    SUSTENTADA = "sustentada"
    CONTRADIZ = "contradiz"
    SEM_EVIDENCIA = "sem_evidencia"


_DESCRICAO_GROUNDING: dict[Grounding, str] = {
    Grounding.SUSTENTADA: "tudo o que a resposta afirma aparece na fala do usuário ou nos dados das tools",
    Grounding.CONTRADIZ: "a resposta afirma algo diferente do que o usuário disse ou do que os dados mostram",
    Grounding.SEM_EVIDENCIA: "a resposta afirma algo que não aparece nem na fala do usuário nem nos dados",
}


def _pedido(estado: Estado) -> str:
    return _PROMPTS["template"].format(
        pergunta_original=estado.get("pergunta_original", ""),
        dados_disponiveis=estado.get("dados_especialista", ""),
        resposta_gerada=estado["resposta_especialista"],
    )


async def _avaliar(estado: Estado) -> Veredito:
    if not jev.disponivel():
        return Veredito.INDISPONIVEL

    try:
        decisoes = await jev.decidir("juiz", _pedido(estado), [
            PerguntaEscolha(name="grounding", instructions=_PROMPTS["grounding"], choices=_DESCRICAO_GROUNDING),
            PerguntaPredicado(name="relevancia", instructions=_PROMPTS["relevancia"]),
            PerguntaPredicado(name="fidelidade", instructions=_PROMPTS["fidelidade"]),
        ])
    except Exception as e:
        logger.warning("Juiz JeV falhou (%s): %s", type(e).__name__, e)
        return Veredito.INDISPONIVEL

    aprovou = (
        Grounding(decisoes.escolha("grounding")) is Grounding.SUSTENTADA
        and decisoes.sim("relevancia")
        and decisoes.sim("fidelidade")
    )

    return Veredito.APROVADO if aprovou else Veredito.REPROVADO


@medir_node(JUIZ)
async def no_juiz(estado: Estado) -> JuizUpdate:
    """
    Aprovado: a transação do turno passa a poder ser confirmada (o runner faz o commit no fim do grafo).
    Reprovado, ou indisponível com escrita pendente: a frase vira a segura e a transação segue
    não aprovada, então o runner desfaz tudo. Indisponível num turno sem escrita deixa a resposta passar:
    não há nada para desfazer.
    """

    veredito = await _avaliar(estado)
    transacao = transacao_atual()
    escreveu = transacao is not None and transacao.escreveu

    if transacao is not None:
        transacao.aprovada = veredito is Veredito.APROVADO

    if veredito is Veredito.REPROVADO or (veredito is Veredito.INDISPONIVEL and escreveu):
        logger.warning("Juiz %s (escrita pendente: %s): turno desfeito, resposta trocada pela segura", veredito, escreveu)
        resposta = FRASE_SEGURA
    else:
        logger.info("Juiz %s", veredito)
        resposta = estado["resposta_especialista"]

    return JuizUpdate(agentes_chamados=[JUIZ], resposta_especialista=resposta)


__all__ = ["Veredito", "no_juiz"]
