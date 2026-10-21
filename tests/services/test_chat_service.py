import pytest

from app.services import chat_service


def _async_retornando(valor):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


async def test_send_message_bloqueia_quando_limite_excedido(monkeypatch):
    monkeypatch.setattr("app.services.chat_service.can_send_message", lambda _uid: False)

    with pytest.raises(chat_service.LimiteDeMensagensExcedido):
        await chat_service.send_message("user-1", "sess-1", "oi")


async def test_send_message_persiste_conteudo_anonimizado_e_resposta(monkeypatch):
    monkeypatch.setattr("app.services.chat_service.can_send_message", lambda _uid: True)
    monkeypatch.setattr(
        "app.services.chat_service.user_service.buscar_perfil", _async_retornando("perfil")
    )
    monkeypatch.setattr(
        "app.services.chat_service.runner.executar",
        _async_retornando("resposta do assessor"),
    )

    salvas = {}

    async def _salvar(user_id, session_id, mensagens):
        salvas.update(user_id=user_id, session_id=session_id, mensagens=mensagens)

    monkeypatch.setattr(
        "app.services.chat_service._salvar_mensagens", _salvar
    )

    resposta = await chat_service.send_message("user-1", "sess-1", "meu cpf é 123.456.789-00")

    assert resposta == "resposta do assessor"
    assert "123.456.789-00" not in salvas["mensagens"][0].content
    assert salvas["mensagens"][1].content == "resposta do assessor"


async def test_send_message_sem_resposta_do_agente_nao_persiste(monkeypatch):
    monkeypatch.setattr("app.services.chat_service.can_send_message", lambda _uid: True)
    monkeypatch.setattr(
        "app.services.chat_service.user_service.buscar_perfil", _async_retornando("perfil")
    )
    monkeypatch.setattr(
        "app.services.chat_service.runner.executar", _async_retornando(None)
    )

    chamou_salvar = False

    async def _salvar(*_args, **_kwargs):
        nonlocal chamou_salvar
        chamou_salvar = True

    monkeypatch.setattr(
        "app.services.chat_service._salvar_mensagens", _salvar
    )

    resposta = await chat_service.send_message("user-1", "sess-1", "oi")

    assert resposta == "Sem resposta."
    assert chamou_salvar is False
