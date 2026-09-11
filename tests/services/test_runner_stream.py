from langchain_core.messages import AIMessage

from assessor_ai.graph.agents.nodes.names import GUARDRAIL_SAIDA, ROTEADOR
from assessor_ai.graph.state import Route
from assessor_ai.identifiers import UserID
from assessor_ai.infra.postgres import current_user_id
from assessor_ai.schemas.execution import (
    AnswerReady,
    NodeFinished,
    NodeStarted,
    RouteSelected,
    RunFailed,
    RunFinished,
    RunStarted,
)
from assessor_ai.schemas.models import ChatMessage, Role
from assessor_ai.services import runner


def _evento(nome, tipo, output=None):
    return {"name": nome, "event": tipo, "data": {"output": output}}


class _FluxoStreamFake:
    def __init__(self, eventos):
        self._eventos = eventos
        self.user_id_durante_stream: UserID | None = None

    async def get(self):
        return self

    async def astream_events(self, estado_inicial, config, version):
        self.user_id_durante_stream = current_user_id()
        for evento in self._eventos:
            yield evento


class _FluxoQueEstoura:
    async def get(self):
        return self

    async def astream_events(self, *args, **kwargs):
        yield _evento(ROTEADOR, "on_chain_start")
        raise RuntimeError("boom")


def _patch_fluxo(monkeypatch, fake):
    monkeypatch.setattr(runner, "fluxo_agentes", fake)


async def _coletar(user_id="11111111-1111-1111-1111-111111111111"):
    return [
        e
        async for e in runner.executar_stream(
            ChatMessage(role=Role.HUMAN, content="oi"), "sess-1", "perfil", user_id
        )
    ]


async def test_executar_stream_caminho_com_especialista(monkeypatch):
    eventos_langgraph = [
        _evento(ROTEADOR, "on_chain_start"),
        _evento(
            ROTEADOR,
            "on_chain_end",
            output={"agentes_chamados": [ROTEADOR], "rota": Route.FINANCEIRO, "pergunta_original": "oi"},
        ),
        _evento(GUARDRAIL_SAIDA, "on_chain_start"),
        _evento(
            GUARDRAIL_SAIDA,
            "on_chain_end",
            output={"agentes_chamados": [GUARDRAIL_SAIDA], "messages": [AIMessage(content="resposta final")]},
        ),
    ]
    _patch_fluxo(monkeypatch, _FluxoStreamFake(eventos_langgraph))

    recebidos = await _coletar()

    assert recebidos[0] == RunStarted()
    assert recebidos[1] == NodeStarted(node=ROTEADOR)
    assert RouteSelected(route=Route.FINANCEIRO) in recebidos
    assert NodeFinished(node=ROTEADOR) in recebidos
    assert NodeFinished(node=GUARDRAIL_SAIDA) in recebidos
    assert recebidos[-2] == AnswerReady(content="resposta final")
    assert recebidos[-1] == RunFinished()


async def test_executar_stream_caminho_fim_direto_no_roteador(monkeypatch):
    eventos_langgraph = [
        _evento(ROTEADOR, "on_chain_start"),
        _evento(
            ROTEADOR,
            "on_chain_end",
            output={
                "agentes_chamados": [ROTEADOR],
                "rota": Route.FIM,
                "pergunta_original": "",
                "messages": [AIMessage(content="oi! como posso ajudar?")],
            },
        ),
    ]
    _patch_fluxo(monkeypatch, _FluxoStreamFake(eventos_langgraph))

    recebidos = await _coletar()

    assert RouteSelected(route=Route.FIM) in recebidos
    assert AnswerReady(content="oi! como posso ajudar?") in recebidos
    assert recebidos[-1] == RunFinished()


async def test_executar_stream_ignora_eventos_de_runnables_internos(monkeypatch):
    eventos_langgraph = [
        _evento(ROTEADOR, "on_chain_start"),
        {"name": "ChatGroq", "event": "on_chat_model_stream", "data": {"chunk": "token interno"}},
        {"name": "RunnableSequence", "event": "on_chain_start", "data": {}},
        _evento(
            ROTEADOR,
            "on_chain_end",
            output={"agentes_chamados": [ROTEADOR], "rota": Route.FAQ, "pergunta_original": "oi"},
        ),
    ]
    _patch_fluxo(monkeypatch, _FluxoStreamFake(eventos_langgraph))

    recebidos = await _coletar()

    tipos = [type(e).__name__ for e in recebidos]
    assert "ChatGroq" not in tipos
    assert tipos == ["RunStarted", "NodeStarted", "RouteSelected", "NodeFinished", "RunFinished"]


async def test_executar_stream_erro_gera_run_failed(monkeypatch):
    _patch_fluxo(monkeypatch, _FluxoQueEstoura())

    recebidos = await _coletar()

    assert recebidos[0] == RunStarted()
    assert recebidos[1] == NodeStarted(node=ROTEADOR)
    assert isinstance(recebidos[-1], RunFailed)
    assert "boom" not in recebidos[-1].message


async def test_executar_stream_restaura_current_user_mesmo_com_erro(monkeypatch):
    _patch_fluxo(monkeypatch, _FluxoQueEstoura())

    anterior = current_user_id()
    await _coletar(user_id="22222222-2222-2222-2222-222222222222")

    assert current_user_id() == anterior


async def test_executar_stream_seta_current_user_durante_execucao(monkeypatch):
    fake = _FluxoStreamFake([])
    _patch_fluxo(monkeypatch, fake)
    user_id = "33333333-3333-3333-3333-333333333333"

    await _coletar(user_id=user_id)

    assert str(fake.user_id_durante_stream) == user_id
