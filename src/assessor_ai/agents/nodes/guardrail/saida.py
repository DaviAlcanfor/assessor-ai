import re

from assessor_ai.agents.nodes.guardrail.schemas import (
    PII,
    PII_USUARIO,
    ResultadoGuardrail,
)
from assessor_ai.agents.nodes.names import NodeName
from assessor_ai.agents.prompts.guardrail import GuardrailPrompts
from assessor_ai.graph.llm import llm_rapido
from assessor_ai.graph.state import Estado
from config.logging import get_logger

logger = get_logger(__name__)

def _saida_ok(conteudo: str) -> ResultadoGuardrail:
    return ResultadoGuardrail(
        bloqueado=False,
        motivo="saida_revisada",
        conteudo=conteudo
    )


def desanonimizar_saida(
    texto: str,
    mapa: dict,
    restaurar: bool = False
) -> str:
    """
    Por padrão omite o valor original,
    não repete dado pessoal na saída.
    """
    
    for token, valor in mapa.items():
        if token not in texto:
            continue

        substituto = valor if restaurar else f"[{token.split('_')[1]} OMITIDO]"
        texto = texto.replace(token, substituto)

    return texto


def _redigir_pii(texto: str, pii_list: list = PII) -> str:
    for tipo, padrao in pii_list:    
        texto = re.sub(padrao, f"[{tipo} OMITIDO]", texto)
    return texto



_FALLBACK_COMPLIANCE = (
    "Não posso confirmar esses detalhes com segurança agora — recomendo conferir com seu "
    "assessor antes de decidir. Investimentos envolvem risco e resultados passados não "
    "garantem retornos futuros."
)


def _revisar_compliance(resposta: str) -> str | None:
    saida = llm_rapido.invoke(
        GuardrailPrompts.COMPLIANCE.format(resposta=resposta)
    ).content.strip()

    if "RESPOSTA:" not in saida:
        return None

    revisada = saida.split("RESPOSTA:", 1)[1].strip()
    return revisada or None


def guardrail_saida(
    resposta: str,
    mapa_pii: dict,
    restaurar_pii: bool = False
) -> ResultadoGuardrail:
    """
    Nunca bloqueia — sempre retorna algum texto. Mas nunca repassa a resposta original
    sem revisão de compliance: se o LLM não seguir o formato esperado (2 tentativas),
    cai num texto seguro genérico em vez de confiar cegamente no que não foi revisado.
    """

    resposta = _redigir_pii(resposta, pii_list=PII_USUARIO)
    resposta = desanonimizar_saida(resposta, mapa_pii, restaurar=restaurar_pii)

    # ponytail: 1 retry fixo, depois fallback seguro — troque por backoff/mais tentativas
    # se o parsing falhar com frequência em produção (hoje é raro, LLM segue o formato quase sempre)
    revisada = _revisar_compliance(resposta) or _revisar_compliance(resposta)

    if revisada is None:
        logger.warning("Guardrail de saída: compliance não retornou formato esperado em 2 tentativas")
        revisada = _FALLBACK_COMPLIANCE

    return _saida_ok(revisada)


def no_guardrail_saida(estado: Estado) -> dict:
    
    logger.info("Revisando resposta do especialista com guardrail de saída...")
    resultado = guardrail_saida(
        estado["resposta_especialista"], 
        estado.get("mapa_pii", {})
    )

    return {
        "agentes_chamados": [NodeName.GUARDRAIL_SAIDA],
        "messages":         [{"role": "assistant", "content": resultado["conteudo"]}],
    }


__all__ = ["no_guardrail_saida"]