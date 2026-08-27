import pytest

from assessor_ai.chat import service


def _async_retornando(valor):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


async def test_obter_usuario_padrao_reaproveita_usuario_existente(monkeypatch):
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.buscar_usuario_existente",
        _async_retornando({"user_id": "user-existente"}),
    )

    assert await service.obter_usuario_padrao() == "user-existente"


async def test_obter_usuario_padrao_cria_usuario_mock_quando_nao_ha_nenhum(monkeypatch):
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.buscar_usuario_existente",
        _async_retornando(None),
    )

    criado = {}

    async def _garantir(user_id, nome, email):
        criado.update(user_id=user_id, nome=nome, email=email)

    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.garantir_usuario", _garantir
    )

    user_id = await service.obter_usuario_padrao()

    assert user_id == criado["user_id"]
    assert criado["nome"] and criado["email"]


async def test_send_message_bloqueia_quando_limite_excedido(monkeypatch):
    monkeypatch.setattr("assessor_ai.chat.service.can_send_message", lambda _uid: False)

    with pytest.raises(service.LimiteDeMensagensExcedido):
        await service.send_message("user-1", "sess-1", "oi")


async def test_send_message_persiste_conteudo_anonimizado_e_resposta(monkeypatch):
    monkeypatch.setattr("assessor_ai.chat.service.can_send_message", lambda _uid: True)
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.buscar_perfil", _async_retornando("perfil")
    )
    monkeypatch.setattr(
        "assessor_ai.chat.service.runner.executar",
        _async_retornando("resposta do assessor"),
    )

    salvas = {}

    async def _salvar(user_id, session_id, mensagens):
        salvas.update(user_id=user_id, session_id=session_id, mensagens=mensagens)

    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.salvar_mensagens", _salvar
    )

    resposta = await service.send_message("user-1", "sess-1", "meu cpf é 123.456.789-00")

    assert resposta == "resposta do assessor"
    assert "123.456.789-00" not in salvas["mensagens"][0].content
    assert salvas["mensagens"][1].content == "resposta do assessor"


async def test_send_message_sem_resposta_do_agente_nao_persiste(monkeypatch):
    monkeypatch.setattr("assessor_ai.chat.service.can_send_message", lambda _uid: True)
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.buscar_perfil", _async_retornando("perfil")
    )
    monkeypatch.setattr(
        "assessor_ai.chat.service.runner.executar", _async_retornando(None)
    )

    chamou_salvar = False

    async def _salvar(*_args, **_kwargs):
        nonlocal chamou_salvar
        chamou_salvar = True

    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.salvar_mensagens", _salvar
    )

    resposta = await service.send_message("user-1", "sess-1", "oi")

    assert resposta == "Sem resposta."
    assert chamou_salvar is False
