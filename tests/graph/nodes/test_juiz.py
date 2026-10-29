from types import SimpleNamespace

import pytest

from app.graph.guardrail.saida import FRASE_SEGURA
from app.graph.nodes import juiz
from app.graph.nodes.juiz import Veredito, no_juiz
from app.infra.postgres import transacao_do_turno

_ESTADO = {
    "pergunta_original": "gastei 2 dólares no café",
    "dados_especialista": "add_transaction({'amount': 2}) -> {'status': 'ok', 'id': 1}",
    "resposta_especialista": "Registrei 2 dólares no café.",
}


class _Decisoes:
    def __init__(self, grounding="sustentada", relevancia=True, fidelidade=True):
        self._respostas = {"relevancia": relevancia, "fidelidade": fidelidade}
        self._grounding = grounding

    def escolha(self, nome):
        assert nome == "grounding"
        return self._grounding

    def sim(self, nome):
        return self._respostas[nome]


def _jev(monkeypatch, decisoes=None, erro=None, disponivel=True):
    async def decidir(uso, entrada, perguntas):
        if erro:
            raise erro
        return decisoes

    monkeypatch.setattr(juiz, "jev", SimpleNamespace(disponivel=lambda: disponivel, decidir=decidir))


async def test_aprovado_mantem_a_frase_e_aprova_a_transacao(monkeypatch):
    _jev(monkeypatch, _Decisoes())

    async with transacao_do_turno() as turno:
        update = await no_juiz(_ESTADO)

    assert update["resposta_especialista"] == _ESTADO["resposta_especialista"]
    assert turno.aprovada is True


@pytest.mark.parametrize(
    "decisoes",
    [
        _Decisoes(grounding="sem_evidencia"),
        _Decisoes(grounding="contradiz"),
        _Decisoes(relevancia=False),
        _Decisoes(fidelidade=False),
    ],
)
async def test_reprovado_troca_a_frase_e_nao_aprova(monkeypatch, decisoes):
    _jev(monkeypatch, decisoes)

    async with transacao_do_turno() as turno:
        update = await no_juiz(_ESTADO)

    assert update["resposta_especialista"] == FRASE_SEGURA
    assert turno.aprovada is False


async def test_juiz_fora_do_ar_com_escrita_pendente_desfaz(monkeypatch):
    _jev(monkeypatch, erro=TimeoutError("gateway"))

    async with transacao_do_turno() as turno:
        turno.escreveu = True
        update = await no_juiz(_ESTADO)

    assert update["resposta_especialista"] == FRASE_SEGURA
    assert turno.aprovada is False


async def test_juiz_sem_chave_com_escrita_pendente_desfaz(monkeypatch):
    _jev(monkeypatch, disponivel=False)

    async with transacao_do_turno() as turno:
        turno.escreveu = True
        update = await no_juiz(_ESTADO)

    assert update["resposta_especialista"] == FRASE_SEGURA


async def test_juiz_fora_do_ar_sem_escrita_deixa_a_resposta_passar(monkeypatch):
    _jev(monkeypatch, erro=TimeoutError("gateway"))

    async with transacao_do_turno() as turno:
        update = await no_juiz(_ESTADO)

    assert update["resposta_especialista"] == _ESTADO["resposta_especialista"]
    assert turno.aprovada is False  # sem veredito, nada é confirmado


async def test_fora_de_uma_transacao_do_turno_so_avalia(monkeypatch):
    _jev(monkeypatch, _Decisoes(grounding="sem_evidencia"))

    update = await no_juiz(_ESTADO)

    assert update["resposta_especialista"] == FRASE_SEGURA


def test_veredito_tem_os_tres_estados():
    assert {v.value for v in Veredito} == {"APROVADO", "REPROVADO", "INDISPONIVEL"}
