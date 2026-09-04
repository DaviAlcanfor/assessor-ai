"""
Os prompts viraram .md carregados por `prompts/loader.py`. Estes testes guardam o contrato
do parser: frontmatter, seções e o envelope montado por `load_prompt`.
"""

import pytest

from assessor_ai.core.prompts.loader import load_prompt, load_sections


@pytest.mark.parametrize(
    "nome", ["router", "financeiro", "agenda", "faq", "orquestrador"]
)
def test_load_prompt_monta_persona_e_papel(nome):
    prompt = load_prompt(nome)

    assert "### PERSONA" in prompt
    assert "### PAPEL" in prompt
    # data/hora fica fora do system_prompt de propósito (agentes compilam uma vez só)
    assert "CONTEXTO TEMPORAL" not in prompt


@pytest.mark.parametrize("nome", ["financeiro", "agenda"])
def test_frontmatter_liga_obrigatoriedade_de_tools(nome):
    assert "### OBRIGATORIEDADE DE TOOLS" in load_prompt(nome)


@pytest.mark.parametrize("nome", ["router", "orquestrador", "faq"])
def test_sem_frontmatter_nao_traz_obrigatoriedade_de_tools(nome):
    assert "### OBRIGATORIEDADE DE TOOLS" not in load_prompt(nome)


@pytest.mark.parametrize(
    "nome", ["router", "financeiro", "agenda", "faq", "orquestrador"]
)
def test_shots_entram_no_prompt(nome):
    assert "FIM DOS EXEMPLOS" in load_prompt(nome)


def test_templates_do_guardrail_tem_os_placeholders_usados_pelos_nos():
    secoes = load_sections("guardrail")

    assert "{mensagem}" in secoes["classificador"]
    assert "{resposta}" in secoes["compliance"]


def test_templates_do_resumidor_tem_os_placeholders_usados_pelos_helpers():
    secoes = load_sections("resumidor")

    assert "{conversa}" in secoes["resumo"]
    assert "{perfil_atual}" in secoes["perfil"]
    assert "{resumo}" in secoes["perfil"]
