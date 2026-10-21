from app.infra.redis import rate_limit as limiter
from app.schemas.execution import (
    AnswerReady,
    RunFailed,
    RunFinished,
    RunStarted,
)
from app.services import chat_service, runner, user_service
from tests.fakes import ConnFake, FakeRedis


def _async(valor=None):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


def _stream_fake(*eventos):
    async def _fn(*_args, **_kwargs):
        for evento in eventos:
            yield evento

    return _fn


async def test_send_message_stream_persiste_uma_vez_ao_terminar_com_sucesso(monkeypatch):
    monkeypatch.setattr(limiter, "redis", ConnFake(FakeRedis()))

    monkeypatch.setattr(
        runner,
        "executar_stream",
        _stream_fake(RunStarted(), AnswerReady(content="resposta ok"), RunFinished()),
    )
    monkeypatch.setattr(user_service, "buscar_perfil", _async("perfil"))

    chamadas_salvar = []

    async def _salvar(user_id, session_id, mensagens):
        chamadas_salvar.append((user_id, session_id, mensagens))

    monkeypatch.setattr(chat_service, "_salvar_mensagens", _salvar)

    eventos = [e async for e in chat_service.send_message_stream("user-1", "chat-1", "oi")]

    assert eventos == [RunStarted(), AnswerReady(content="resposta ok"), RunFinished()]
    assert len(chamadas_salvar) == 1
    _, _, mensagens = chamadas_salvar[0]
    assert mensagens[-1].content == "resposta ok"


async def test_send_message_stream_rate_limit_nao_persiste_e_emite_run_failed(monkeypatch):
    fake_redis = FakeRedis()
    # já no limite: N_MESSAGES_ACCEPTED chamadas de incr antes desta
    for _ in range(limiter.N_MESSAGES_ACCEPTED):
        fake_redis.incr(limiter._chave_mensagem("user-1"))
    monkeypatch.setattr(limiter, "redis", ConnFake(fake_redis))

    chamado = False

    async def _salvar(*_args, **_kwargs):
        nonlocal chamado
        chamado = True

    monkeypatch.setattr(chat_service, "_salvar_mensagens", _salvar)

    eventos = [e async for e in chat_service.send_message_stream("user-1", "chat-1", "oi")]

    assert len(eventos) == 1
    assert isinstance(eventos[0], RunFailed)
    assert chamado is False


async def test_send_message_stream_run_failed_do_agente_nao_persiste(monkeypatch):
    monkeypatch.setattr(limiter, "redis", ConnFake(FakeRedis()))
    monkeypatch.setattr(
        runner, "executar_stream", _stream_fake(RunStarted(), RunFailed(message="deu ruim"))
    )
    monkeypatch.setattr(user_service, "buscar_perfil", _async("perfil"))

    chamado = False

    async def _salvar(*_args, **_kwargs):
        nonlocal chamado
        chamado = True

    monkeypatch.setattr(chat_service, "_salvar_mensagens", _salvar)

    eventos = [e async for e in chat_service.send_message_stream("user-1", "chat-1", "oi")]

    assert eventos == [RunStarted(), RunFailed(message="deu ruim")]
    assert chamado is False
