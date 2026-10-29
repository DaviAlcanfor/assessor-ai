import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.domain.errors import UsuarioDaSessaoNaoDefinido
from app.domain.models.chat import ChatMessage, Role
from app.infra.context import current_user_id
from app.infra.postgres import transacao_atual
from app.services import runner


class _FluxoFake:
    def __init__(self, resposta: str):
        self.resposta = resposta
        self.recebido = None
        self.user_id_durante_invoke = None

    async def ainvoke(self, estado_inicial, config):
        self.recebido = (estado_inicial, config)
        self.user_id_durante_invoke = current_user_id()
        return {"messages": [HumanMessage(content="oi"), AIMessage(content=self.resposta)]}


def _patch_fluxo(monkeypatch, fake):
    class _Fluxo:
        async def get(self):
            return fake

    monkeypatch.setattr("app.services.runner.fluxo_agentes", _Fluxo())


async def test_executar_extrai_ultima_resposta_da_ia(monkeypatch):
    fake = _FluxoFake("resposta do assessor")
    _patch_fluxo(monkeypatch, fake)

    resposta = await runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"),
        session_id="sess-1",
        perfil_usuario="perfil x",
        user_id="11111111-1111-1111-1111-111111111111",
    )

    assert resposta == "resposta do assessor"


async def test_executar_seta_current_user_durante_invoke_e_restaura_depois(monkeypatch):
    fake = _FluxoFake("ok")
    _patch_fluxo(monkeypatch, fake)
    user_id = "22222222-2222-2222-2222-222222222222"

    await runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"), "sess-1", "perfil", user_id
    )

    assert str(fake.user_id_durante_invoke) == user_id
    with pytest.raises(UsuarioDaSessaoNaoDefinido):  # o escopo não vaza pra fora do turno
        current_user_id()


async def test_executar_passa_thread_id_tags_e_metadata_pro_invoke(monkeypatch):
    fake = _FluxoFake("ok")
    _patch_fluxo(monkeypatch, fake)

    user_id = "33333333-3333-3333-3333-333333333333"
    await runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"), "sess-42", "perfil", user_id
    )

    _, config = fake.recebido
    assert config["configurable"]["thread_id"] == "sess-42"
    assert config["metadata"] == {"user_id": user_id, "session_id": "sess-42"}


async def test_executar_sem_ai_message_retorna_none(monkeypatch):
    class _FluxoSemResposta:
        async def ainvoke(self, *_args, **_kwargs):
            return {"messages": [HumanMessage(content="oi")]}

    _patch_fluxo(monkeypatch, _FluxoSemResposta())

    resposta = await runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"),
        "sess-1",
        "perfil",
        "44444444-4444-4444-4444-444444444444",
    )

    assert resposta is None


async def test_executar_abre_a_transacao_do_turno_so_durante_o_invoke(monkeypatch):
    visto = {}

    class _FluxoQueOlhaATransacao:
        async def ainvoke(self, *_args, **_kwargs):
            visto["durante"] = transacao_atual()
            return {"messages": [AIMessage(content="ok")]}

    _patch_fluxo(monkeypatch, _FluxoQueOlhaATransacao())

    await runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"), "sess-1", "perfil", "55555555-5555-5555-5555-555555555555"
    )

    assert visto["durante"] is not None
    assert transacao_atual() is None
