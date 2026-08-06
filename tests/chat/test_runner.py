from langchain_core.messages import AIMessage, HumanMessage

from assessor_ai.chat import runner
from assessor_ai.chat.models import ChatMessage, Role
from assessor_ai.tools.postgres.connection import current_user_id


class _FluxoFake:
    def __init__(self, resposta: str):
        self.resposta = resposta
        self.recebido = None
        self.user_id_durante_invoke = None

    def invoke(self, estado_inicial, config):
        self.recebido = (estado_inicial, config)
        self.user_id_durante_invoke = current_user_id()
        return {"messages": [HumanMessage(content="oi"), AIMessage(content=self.resposta)]}


def test_executar_extrai_ultima_resposta_da_ia(monkeypatch):
    fake = _FluxoFake("resposta do assessor")
    monkeypatch.setattr("assessor_ai.chat.runner.fluxo_agentes", fake)

    resposta = runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"),
        session_id="sess-1",
        perfil_usuario="perfil x",
        user_id="11111111-1111-1111-1111-111111111111",
    )

    assert resposta == "resposta do assessor"


def test_executar_seta_current_user_durante_invoke_e_restaura_depois(monkeypatch):
    fake = _FluxoFake("ok")
    monkeypatch.setattr("assessor_ai.chat.runner.fluxo_agentes", fake)
    user_id = "22222222-2222-2222-2222-222222222222"

    anterior = current_user_id()
    runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"), "sess-1", "perfil", user_id
    )

    assert str(fake.user_id_durante_invoke) == user_id
    assert current_user_id() == anterior


def test_executar_passa_thread_id_tags_e_metadata_pro_invoke(monkeypatch):
    fake = _FluxoFake("ok")
    monkeypatch.setattr("assessor_ai.chat.runner.fluxo_agentes", fake)

    user_id = "33333333-3333-3333-3333-333333333333"
    runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"), "sess-42", "perfil", user_id
    )

    _, config = fake.recebido
    assert config["configurable"]["thread_id"] == "sess-42"
    assert config["metadata"] == {"user_id": user_id, "session_id": "sess-42"}


def test_executar_sem_ai_message_retorna_none(monkeypatch):
    class _FluxoSemResposta:
        def invoke(self, *_args, **_kwargs):
            return {"messages": [HumanMessage(content="oi")]}

    monkeypatch.setattr("assessor_ai.chat.runner.fluxo_agentes", _FluxoSemResposta())

    resposta = runner.executar(
        ChatMessage(role=Role.HUMAN, content="oi"),
        "sess-1",
        "perfil",
        "44444444-4444-4444-4444-444444444444",
    )

    assert resposta is None
