from datetime import UTC, datetime

from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.graph.agents.prompts import loader
from assessor_ai.graph.agents.prompts.loader import contexto_do_turno, contexto_temporal


class _DatetimeFake:
    @staticmethod
    def now(tz=None):
        return datetime(2030, 7, 15, 10, 30, tzinfo=UTC)


def test_contexto_temporal_e_calculado_na_chamada(monkeypatch):
    """
    Regressão: a data era calculada no import do módulo e congelava junto com o
    processo (a API ficava com "hoje" travado na data do deploy). Se voltar a ser
    constante de módulo, o patch abaixo não muda nada e o teste quebra.
    """

    monkeypatch.setattr(loader, "datetime", _DatetimeFake)

    assert "2030" in contexto_temporal()


def test_contexto_do_turno_inclui_perfil_e_pergunta():
    contexto = contexto_do_turno(
        perfil_usuario="Prefere respostas curtas.",
        pergunta_original="quanto gastei na viagem?",
    )

    assert "Prefere respostas curtas." in contexto
    assert "quanto gastei na viagem?" in contexto


def test_contexto_do_turno_omite_blocos_vazios():
    contexto = contexto_do_turno()

    assert "PERFIL DO USUÁRIO" not in contexto
    assert "PERGUNTA ENCAMINHADA" not in contexto
    assert "CONTEXTO TEMPORAL" in contexto


def test_mensagens_com_contexto_preserva_historico_e_poe_sistema_na_frente():
    estado = {
        "messages": [{"role": "human", "content": "oi"}],
        "perfil_usuario": "Mora sozinho.",
        "pergunta_original": "quanto gastei?",
    }

    mensagens = mensagens_com_contexto(estado)

    assert mensagens[0]["role"] == "system"
    assert "Mora sozinho." in mensagens[0]["content"]
    assert "quanto gastei?" in mensagens[0]["content"]
    assert mensagens[1:] == estado["messages"]


def test_mensagens_com_contexto_sem_pergunta_para_o_orquestrador():
    estado = {
        "messages": [],
        "perfil_usuario": "Mora sozinho.",
        "pergunta_original": "quanto gastei?",
    }

    contexto = mensagens_com_contexto(estado, incluir_pergunta=False)[0]["content"]

    assert "Mora sozinho." in contexto
    assert "quanto gastei?" not in contexto


def test_estado_sem_perfil_nao_quebra():
    mensagens = mensagens_com_contexto({"messages": []})

    assert mensagens[0]["role"] == "system"
    assert "CONTEXTO TEMPORAL" in mensagens[0]["content"]
