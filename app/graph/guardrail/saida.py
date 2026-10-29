import re

from langchain_core.messages import AIMessage

from app.domain.privacy import PII, PII_USUARIO, MapaPII, PIIPattern
from app.graph.guardrail.schemas import ResultadoGuardrail
from app.graph.llm import llm_rapido
from app.graph.names import GUARDRAIL_SAIDA
from app.graph.prompts.loader import load_sections
from app.graph.state import Estado, GuardrailSaidaUpdate
from app.infra.logging import Logging
from app.telemetry import medir_node

logger = Logging.get_logger(__name__)

_GUARDRAIL = load_sections("guardrail")

def _saida_ok(conteudo: str) -> ResultadoGuardrail:
    return ResultadoGuardrail(
        bloqueado=False,
        motivo="saida_revisada",
        conteudo=conteudo
    )


def desanonimizar_saida(
    texto: str,
    mapa: MapaPII,
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


def _redigir_pii(texto: str, pii_list: list[PIIPattern] = PII) -> str:
    for tipo, padrao in pii_list:    
        texto = re.sub(padrao, f"[{tipo} OMITIDO]", texto)
    return texto



FRASE_SEGURA = (
    "Não tenho evidência suficiente para afirmar isso, e nenhuma alteração deste pedido foi mantida "
    "no seu financeiro ou na sua agenda."
)

_FALLBACK_COMPLIANCE = (
    "Não posso confirmar esses detalhes com segurança agora — recomendo conferir com seu "
    "assessor antes de decidir. Investimentos envolvem risco e resultados passados não "
    "garantem retornos futuros."
)


async def _revisar_compliance(resposta: str) -> str | None:
    revisao = await llm_rapido.ainvoke(
        _GUARDRAIL["compliance"].format(resposta=resposta)
    )
    saida = revisao.text.strip()

    if "RESPOSTA:" not in saida:
        return None

    revisada = saida.split("RESPOSTA:", 1)[1].strip()
    return revisada or None


async def guardrail_saida(
    resposta: str,
    mapa_pii: MapaPII,
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
    revisada = await _revisar_compliance(resposta) or await _revisar_compliance(resposta)

    if revisada is None:
        logger.warning("Guardrail de saída: compliance não retornou formato esperado em 2 tentativas")
        revisada = _FALLBACK_COMPLIANCE

    return _saida_ok(revisada)


@medir_node(GUARDRAIL_SAIDA)
async def no_guardrail_saida(estado: Estado) -> GuardrailSaidaUpdate:

    # Frase que o juiz já trocou: é fixa e não tem dado pessoal, então não gasta uma revisão de LLM
    # (que ainda poderia reescrevê-la). Comparar o texto evita um campo de estado que sobraria no checkpoint.
    if estado["resposta_especialista"] == FRASE_SEGURA:
        return GuardrailSaidaUpdate(
            agentes_chamados=[GUARDRAIL_SAIDA],
            messages=[AIMessage(content=FRASE_SEGURA)],
        )

    logger.info("Revisando resposta do especialista com guardrail de saída...")
    resultado = await guardrail_saida(
        estado["resposta_especialista"],
        estado.get("mapa_pii", {})
    )

    return GuardrailSaidaUpdate(
        agentes_chamados=[GUARDRAIL_SAIDA],
        messages=[AIMessage(content=resultado["conteudo"])],
    )


__all__ = ["FRASE_SEGURA", "no_guardrail_saida"]