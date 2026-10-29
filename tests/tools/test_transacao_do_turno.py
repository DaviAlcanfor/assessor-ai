"""
A invariante do juiz, nas quatro escritas do Postgres: turno recusado não deixa linha nenhuma; turno
aprovado grava uma vez. Passa pelo `PostgresConn.session()` de verdade (a mesma porta de produção),
com SQLite no lugar do Postgres. Cada teste usa um marcador único no `source_text` pra achar a linha
no banco sem depender do que mais existe nele.
"""

from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.graph.tools.agenda.tools import AgendaTools
from app.graph.tools.financeiro.tools import FinanceiroTools
from app.infra.postgres import PostgresConn, transacao_do_turno
from app.infra.postgres.models import Event, Transaction
from app.repositories.agenda_repository import AgendaRepository
from app.repositories.financeiro_repository import FinanceiroRepository
from app.services.agenda_service import AgendaService
from app.services.financeiro_service import FinanceiroService


@pytest.fixture
def conn(db_session) -> PostgresConn:
    """O `PostgresConn` real, só com o engine trocado pelo SQLite do `db_session`."""

    engine = db_session.get_bind()

    # SAVEPOINT no pysqlite: o driver só abre transação antes de um INSERT/UPDATE, então o SAVEPOINT roda
    # fora de uma e o RELEASE dele confirma tudo. É limitação do driver de teste (o psycopg do Postgres não
    # tem isso). Receita da doc do SQLAlchemy: o driver para de decidir sozinho e o BEGIN é emitido na mão.
    engine.raw_connection().driver_connection.isolation_level = None
    event.listen(engine, "begin", lambda c: c.exec_driver_sql("BEGIN"))

    conn = PostgresConn()
    conn._engine = engine
    conn._session_factory = sessionmaker(bind=engine)
    return conn


@pytest.fixture
def financeiro(conn) -> FinanceiroTools:
    return FinanceiroTools(FinanceiroService(FinanceiroRepository(conn=conn)))


@pytest.fixture
def agenda(conn) -> AgendaTools:
    return AgendaTools(AgendaService(AgendaRepository(conn=conn)))


@pytest.fixture
def marcador() -> str:
    return f"marcador-{uuid4().hex}"


def _transacoes(db_session, marcador: str) -> list[Transaction]:
    db_session.expire_all()
    return db_session.query(Transaction).filter(Transaction.source_text == marcador).all()


def _eventos(db_session, marcador: str) -> list[Event]:
    db_session.expire_all()
    return db_session.query(Event).filter(Event.source_text == marcador).all()


_INICIO = "2026-02-01T10:00:00+00:00"


async def test_add_transaction_recusado_nao_deixa_linha(financeiro, db_session, marcador):
    async with transacao_do_turno():
        resultado = await financeiro.add_transaction(amount=2, source_text=marcador)

    assert resultado["status"] == "ok"
    assert _transacoes(db_session, marcador) == []


async def test_add_transaction_aprovado_grava_uma_vez(financeiro, db_session, marcador):
    async with transacao_do_turno() as turno:
        await financeiro.add_transaction(amount=2, source_text=marcador)
        turno.aprovada = True

    assert len(_transacoes(db_session, marcador)) == 1


async def test_update_transaction_recusado_mantem_o_valor_antigo(financeiro, db_session, marcador):
    criada = await financeiro.add_transaction(amount=10, source_text=marcador)  # fora do turno: commit direto

    async with transacao_do_turno():
        atualizada = await financeiro.update_transaction(id=criada["id"], amount=99)

    assert atualizada["rows_affected"] == 1
    assert float(_transacoes(db_session, marcador)[0].amount) == 10


async def test_update_transaction_aprovado_aplica_a_mudanca(financeiro, db_session, marcador):
    criada = await financeiro.add_transaction(amount=10, source_text=marcador)

    async with transacao_do_turno() as turno:
        await financeiro.update_transaction(id=criada["id"], amount=99)
        turno.aprovada = True

    assert float(_transacoes(db_session, marcador)[0].amount) == 99


async def test_add_event_recusado_nao_deixa_evento(agenda, db_session, marcador):
    async with transacao_do_turno():
        resultado = await agenda.add_event(title="Dentista", start_time=_INICIO, source_text=marcador, notes="")

    assert resultado["status"] == "ok"
    assert _eventos(db_session, marcador) == []


async def test_add_event_aprovado_grava_uma_vez(agenda, db_session, marcador):
    async with transacao_do_turno() as turno:
        await agenda.add_event(title="Dentista", start_time=_INICIO, source_text=marcador, notes="")
        turno.aprovada = True

    assert len(_eventos(db_session, marcador)) == 1


async def test_update_event_recusado_mantem_o_titulo_antigo(agenda, db_session, marcador):
    criado = await agenda.add_event(title="Dentista", start_time=_INICIO, source_text=marcador, notes="")

    async with transacao_do_turno():
        await agenda.update_event(id=criado["id"], title="Cirurgia")

    assert _eventos(db_session, marcador)[0].title == "Dentista"


async def test_update_event_aprovado_aplica_a_mudanca(agenda, db_session, marcador):
    criado = await agenda.add_event(title="Dentista", start_time=_INICIO, source_text=marcador, notes="")

    async with transacao_do_turno() as turno:
        await agenda.update_event(id=criado["id"], title="Cirurgia")
        turno.aprovada = True

    assert _eventos(db_session, marcador)[0].title == "Cirurgia"


async def test_excecao_no_turno_desfaz_mesmo_com_juiz_aprovado(financeiro, db_session, marcador):
    with pytest.raises(RuntimeError):
        async with transacao_do_turno() as turno:
            await financeiro.add_transaction(amount=2, source_text=marcador)
            turno.aprovada = True
            raise RuntimeError("guardrail de saída caiu")

    assert _transacoes(db_session, marcador) == []


async def test_turno_sem_veredito_desfaz(financeiro, db_session, marcador):
    """Ninguém marcou `aprovada` (juiz fora do ar, caminho que pulou o juiz): o padrão é desfazer."""

    async with transacao_do_turno():
        await financeiro.add_transaction(amount=2, source_text=marcador)

    assert _transacoes(db_session, marcador) == []


async def test_tool_que_falha_nao_desfaz_a_escrita_anterior_do_turno(financeiro, db_session, marcador):
    async with transacao_do_turno() as turno:
        await financeiro.add_transaction(amount=2, source_text=marcador)
        falha = await financeiro.update_transaction(match_text="nada-assim", date_local="2020-01-01", amount=1)
        turno.aprovada = True

    assert falha["status"] == "error"
    assert len(_transacoes(db_session, marcador)) == 1


async def test_leitura_do_turno_enxerga_a_escrita_ainda_nao_confirmada(financeiro, marcador):
    async with transacao_do_turno():
        await financeiro.add_transaction(amount=2, source_text=marcador)
        consulta = await financeiro.query_transactions(source_text=marcador)

    assert consulta["total_records"] == 1


async def test_escrita_marca_o_turno_e_leitura_nao(financeiro, marcador):
    async with transacao_do_turno() as turno:
        await financeiro.query_transactions()
        assert turno.escreveu is False

        await financeiro.add_transaction(amount=2, source_text=marcador)
        assert turno.escreveu is True


async def test_fora_do_turno_a_escrita_confirma_na_hora(financeiro, db_session, marcador):
    """MCP e qualquer chamada sem transação do turno seguem como antes: commit dentro da operação."""

    await financeiro.add_transaction(amount=2, source_text=marcador)

    assert len(_transacoes(db_session, marcador)) == 1
