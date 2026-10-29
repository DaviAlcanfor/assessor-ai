from datetime import UTC, datetime

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.nodes.contexto import mensagens_com_contexto, responder_com_evidencias
from app.graph.prompts import loader
from app.graph.prompts.loader import contexto_do_turno, contexto_temporal


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

    assert mensagens[0].type == "system"
    assert "Mora sozinho." in mensagens[0].content
    assert "quanto gastei?" in mensagens[0].content
    assert mensagens[1:] == estado["messages"]


def test_mensagens_com_contexto_sem_pergunta_para_o_orquestrador():
    estado = {
        "messages": [],
        "perfil_usuario": "Mora sozinho.",
        "pergunta_original": "quanto gastei?",
    }

    contexto = mensagens_com_contexto(estado, incluir_pergunta=False)[0].content

    assert "Mora sozinho." in contexto
    assert "quanto gastei?" not in contexto


def test_estado_sem_perfil_nao_quebra():
    mensagens = mensagens_com_contexto({"messages": []})

    assert mensagens[0].type == "system"
    assert "CONTEXTO TEMPORAL" in mensagens[0].content


async def test_responder_com_evidencias_junta_tool_args_e_retorno():
    class _AgenteFake:
        async def ainvoke(self, _entrada):
            return {"messages": [
                AIMessage(content="", tool_calls=[{"id": "c1", "name": "add_transaction", "args": {"amount": 2}}]),
                ToolMessage(content="{'status': 'ok', 'id': 7}", name="add_transaction", tool_call_id="c1"),
                AIMessage(content="Registrei."),
            ]}

    resposta, evidencias = await responder_com_evidencias(_AgenteFake(), [])

    assert resposta == "Registrei."
    assert evidencias == "add_transaction({'amount': 2}) -> {'status': 'ok', 'id': 7}"


async def test_responder_com_evidencias_sem_tool_usa_a_propria_resposta():
    class _AgenteFake:
        async def ainvoke(self, _entrada):
            return {"messages": [AIMessage(content="Não sei.")]}

    resposta, evidencias = await responder_com_evidencias(_AgenteFake(), [])

    assert (resposta, evidencias) == ("Não sei.", "Não sei.")
