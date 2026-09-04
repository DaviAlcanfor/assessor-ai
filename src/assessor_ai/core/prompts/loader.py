"""
Único módulo Python em core/prompts/ — o resto da pasta é só .md.

Cada .md pode ter um header `---\nchave: valor\n---` (metadados, hoje só
`usa_tools_obrigatorias`) seguido de seções `## NOME` (PAPEL, SHOTS, CLASSIFICADOR...).
`load_prompt()` monta o system_prompt completo (persona + [obrigatoriedade de tools] +
papel + [shots]) a partir das seções PAPEL/SHOTS; `load_sections()` devolve as seções
cruas, pra quem precisa de outra seção (templates do guardrail e do resumidor) ou não
quer o envelope de persona.

O bloco de data/hora NÃO entra aqui de propósito: `graph/agents.py` compila os agentes no
import, então qualquer data no system_prompt congela junto com o processo (a API ficaria
com "hoje" travado na data do deploy). Ele vai em `contexto_do_turno()`, montado a cada
turno pelos nós.
"""

from datetime import UTC, datetime
from pathlib import Path

_PASTA = Path(__file__).parent
_MARCADOR_SECAO = "## "
_MARCADOR_FRONTMATTER = "---"

PERSONA_SISTEMA = """
### PERSONA
Você é o Assessor.AI — um assistente pessoal de compromissos e finanças. Você é especialista em gestão financeira e
organização de rotina. Sua principal característica é a objetividade e a confiabilidade. Você é empático, direto e
responsável, sempre buscando fornecer as melhores informações e conselhos sem ser prolixo. Seu objetivo é ser um parceiro
confiável para o usuário, auxiliando-o a tomar decisões financeiras conscientes e a manter a vida organizada.
"""

OBRIGATORIEDADE_TOOLS = """
### OBRIGATORIEDADE DE TOOLS
- TODA resposta que contenha valores, datas ou registros DEVE ser precedida
  de uma chamada de tool nesta mesma execução.
- NUNCA use valores do histórico de conversa como fonte de dados — histórico
  serve apenas para entender o contexto da pergunta.
- Se a tool retornar erro ou nenhum resultado, informe isso no campo "resposta".
  Jamais invente um valor substituto.
"""


def _parse_frontmatter(texto: str) -> tuple[dict[str, str], str]:
    linhas = texto.splitlines()

    if not linhas or linhas[0].strip() != _MARCADOR_FRONTMATTER:
        return {}, texto

    for i, linha in enumerate(linhas[1:], start=1):
        if linha.strip() != _MARCADOR_FRONTMATTER:
            continue

        metadados = {}
        for linha_meta in linhas[1:i]:
            if ":" in linha_meta:
                chave, valor = linha_meta.split(":", 1)
                metadados[chave.strip()] = valor.strip()

        return metadados, "\n".join(linhas[i + 1 :])

    return {}, texto


def _parse_secoes(texto: str) -> dict[str, str]:
    secoes: dict[str, str] = {}
    nome_atual: str | None = None
    linhas_atuais: list[str] = []

    for linha in texto.splitlines():
        if linha.startswith(_MARCADOR_SECAO):
            if nome_atual:
                secoes[nome_atual] = "\n".join(linhas_atuais).strip()
            nome_atual = linha.removeprefix(_MARCADOR_SECAO).strip().lower()
            linhas_atuais = []
        elif nome_atual:
            linhas_atuais.append(linha)

    if nome_atual:
        secoes[nome_atual] = "\n".join(linhas_atuais).strip()

    return secoes


def _ler(nome: str) -> tuple[dict[str, str], dict[str, str]]:
    texto = (_PASTA / f"{nome}.md").read_text(encoding="utf-8")
    metadados, corpo = _parse_frontmatter(texto)
    return metadados, _parse_secoes(corpo)


def load_sections(nome: str) -> dict[str, str]:
    """Seções cruas do .md (sem persona), pra quem monta o prompt na mão — os templates
    de guardrail (CLASSIFICADOR/COMPLIANCE) e de resumidor (RESUMO/PERFIL)."""

    _, secoes = _ler(nome)
    return secoes


def load_prompt(nome: str) -> str:
    """System prompt completo: persona + [obrigatoriedade de tools, se o frontmatter
    marcar] + papel + [shots]."""

    metadados, secoes = _ler(nome)

    partes = [PERSONA_SISTEMA]

    if metadados.get("usa_tools_obrigatorias") == "true":
        partes.append(OBRIGATORIEDADE_TOOLS)

    partes.append(f"### PAPEL\n{secoes.get('papel', '')}")

    if secoes.get("shots"):
        partes.append(secoes["shots"])

    return "\n\n".join(partes)


def contexto_temporal() -> str:
    """Bloco de data/hora, calculado na hora da chamada — nunca no import (ver docstring
    do módulo)."""

    agora = datetime.now(UTC).astimezone()
    formatada = agora.strftime("%A, %d de %B de %Y — %H:%M:%S %Z")

    return f"""### CONTEXTO TEMPORAL
Data e hora atual (fornecida pelo sistema): {formatada}
Use esta referência para interpretar "hoje", "ontem", "semana passada",
calcular datas relativas e preencher timestamps nas operações."""


def contexto_do_turno(perfil_usuario: str = "", pergunta_original: str = "") -> str:
    """
    Contexto que muda a cada turno e por isso não cabe no system_prompt: os agentes são
    compilados uma única vez, no import de `graph/agents.py`. Entra como mensagem de
    sistema extra no invoke do nó.
    """

    blocos = [contexto_temporal()]

    if perfil_usuario:
        blocos.append(f"### PERFIL DO USUÁRIO\n{perfil_usuario}")

    if pergunta_original:
        blocos.append(f"### PERGUNTA ENCAMINHADA PELO ROTEADOR\n{pergunta_original}")

    return "\n\n".join(blocos)


__all__ = ["contexto_do_turno", "contexto_temporal", "load_prompt", "load_sections"]
