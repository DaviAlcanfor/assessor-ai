"""
Os prompts viraram .md carregados por `prompts/loader.py`. Estes testes guardam o contrato
do parser: frontmatter, seções e o envelope montado por `load_prompt`.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from assessor_ai.graph.agents.prompts import loader
from assessor_ai.graph.agents.prompts.loader import load_prompt, load_sections


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


def test_contexto_temporal_usa_fuso_configurado_nao_do_processo(monkeypatch):
    # `.astimezone()` sem fuso explícito usa o fuso local do SO do processo — que pode até
    # coincidir com America/Sao_Paulo na máquina de quem roda o teste, mascarando o bug em
    # deploys onde não coincide (UTC, por exemplo). Por isso o teste força `_FUSO_LOCAL` pra
    # um fuso bem distante de qualquer default plausível (UTC+14), pra provar que o código
    # respeita o fuso configurado e não o do host — não depender de sorte de ambiente.
    fixo_utc = datetime(2026, 1, 15, 1, 0, tzinfo=UTC)

    class _DatetimeFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixo_utc

    monkeypatch.setattr(loader, "datetime", _DatetimeFixo)
    monkeypatch.setattr(loader, "_FUSO_LOCAL", ZoneInfo("Pacific/Kiritimati"))

    texto = loader.contexto_temporal()

    assert "15:00:00" in texto
