import pytest

from assessor_ai.chat import service


def test_send_message_bloqueia_quando_limite_excedido(monkeypatch):
    monkeypatch.setattr("assessor_ai.chat.service.can_send_message", lambda _uid: False)

    with pytest.raises(service.LimiteDeMensagensExcedido):
        service.send_message("user-1", "sess-1", "oi")


def test_send_message_persiste_conteudo_anonimizado_e_resposta(monkeypatch):
    monkeypatch.setattr("assessor_ai.chat.service.can_send_message", lambda _uid: True)
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.buscar_perfil", lambda _uid: "perfil"
    )
    monkeypatch.setattr(
        "assessor_ai.chat.service.runner.executar",
        lambda *_args, **_kwargs: "resposta do assessor",
    )

    salvas = {}
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.salvar_mensagens",
        lambda user_id, session_id, mensagens: salvas.update(
            user_id=user_id, session_id=session_id, mensagens=mensagens
        ),
    )

    resposta = service.send_message("user-1", "sess-1", "meu cpf é 123.456.789-00")

    assert resposta == "resposta do assessor"
    assert "123.456.789-00" not in salvas["mensagens"][0].content
    assert salvas["mensagens"][1].content == "resposta do assessor"


def test_send_message_sem_resposta_do_agente_nao_persiste(monkeypatch):
    monkeypatch.setattr("assessor_ai.chat.service.can_send_message", lambda _uid: True)
    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.buscar_perfil", lambda _uid: "perfil"
    )
    monkeypatch.setattr(
        "assessor_ai.chat.service.runner.executar", lambda *_args, **_kwargs: None
    )

    chamou_salvar = False

    def _salvar(*_args, **_kwargs):
        nonlocal chamou_salvar
        chamou_salvar = True

    monkeypatch.setattr(
        "assessor_ai.chat.service.repositories.salvar_mensagens", _salvar
    )

    resposta = service.send_message("user-1", "sess-1", "oi")

    assert resposta == "Sem resposta."
    assert chamou_salvar is False
