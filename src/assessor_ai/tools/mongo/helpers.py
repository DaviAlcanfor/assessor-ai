from assessor_ai.agents.prompts.loader import load_sections
from assessor_ai.graph.llm import llm_rapido
from config.logging import get_logger

log = get_logger(__name__)

_RESUMIDOR = load_sections("resumidor")


def _formatar_conversa(mensagens: list[dict]) -> str:
    linhas = []

    for msg in mensagens:
        linhas.append(f"{msg['role']}: {msg['content']}")

    return "\n".join(linhas)


def _gerar_resumo(mensagens: list[dict]) -> str:
    log.info("Resumindo conversa...")

    conversa = _formatar_conversa(mensagens)

    return llm_rapido.invoke(
        _RESUMIDOR["resumo"].format(conversa=conversa)
    ).content.strip()


def _gerar_perfil(perfil_atual: str, resumo: str) -> str:
    log.info("Atualizando perfil do usuário...")

    return llm_rapido.invoke(
        _RESUMIDOR["perfil"].format(perfil_atual=perfil_atual, resumo=resumo)
    ).content.strip()
