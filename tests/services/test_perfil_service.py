"""PerfilService e PerfilTools: o perfil do agente é sempre o do usuário do turno (`session_context`)."""

from app.graph.tools.perfil.tools import PerfilTools
from app.infra.context import session_context
from app.services.perfil_service import PerfilService
from tests.repositories.test_perfil_repository import _repo

USER_1 = "11111111-1111-1111-1111-111111111111"
USER_2 = "22222222-2222-2222-2222-222222222222"


def _service() -> PerfilService:
    return PerfilService(_repo())


async def test_consultar_sem_cadastro_retorna_cadastrado_false():
    with session_context(USER_1):
        resultado = await _service().consultar_para_agente("qualquer pergunta")

    assert resultado == {"cadastrado": False}


async def test_consultar_retorna_dados_e_preferencias_do_usuario_do_turno():
    servico = _service()
    await servico.salvar(USER_1, 4200.0, "juntar para viagem", "baixa", "nao quero investimento agressivo")

    with session_context(USER_1):
        resultado = await servico.consultar_para_agente("cripto compensa?")

    assert resultado["cadastrado"] is True
    assert resultado["renda_mensal"] == 4200.0
    assert resultado["tolerancia_risco"] == "baixa"
    assert resultado["preferencias_relevantes"] == ["nao quero investimento agressivo"]


async def test_consultar_nao_ve_perfil_de_outro_usuario():
    servico = _service()
    await servico.salvar(USER_1, 4200.0, "viagem", "baixa", "restricao do user 1")

    with session_context(USER_2):
        resultado = await servico.consultar_para_agente("pergunta qualquer")

    assert resultado == {"cadastrado": False}


async def test_a_tool_embrulha_o_service_em_response_ok():
    servico = _service()
    await servico.salvar(USER_1, 4200.0, "viagem", "baixa", None)

    with session_context(USER_1):
        resposta = await PerfilTools(servico).consultar_perfil_financeiro("o que eu ganho?")

    assert resposta["status"] == "ok"
    assert resposta["cadastrado"] is True


async def test_a_tool_sem_escopo_de_usuario_devolve_erro_e_nao_excecao():
    resposta = await PerfilTools(_service()).consultar_perfil_financeiro("sem escopo")

    assert resposta["status"] == "error"
