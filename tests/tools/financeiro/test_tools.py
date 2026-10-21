from datetime import UTC, datetime
from uuid import UUID

from app.infra.context import session_context
from app.infra.postgres.models import (
    PaymentType,
    Transaction,
    TransactionType,
)

OUTRO_USUARIO = UUID("11111111-1111-1111-1111-111111111111")


async def test_add_transaction_resolve_categoria_por_nome(financeiro, db_session, categoria):
    resultado = await financeiro.add_transaction(amount=50.0, source_text="mercado", category_name="Mercado")

    assert resultado["status"] == "ok"
    tx = db_session.get(Transaction, resultado["id"])
    assert tx.category_id == categoria.id


async def test_add_transaction_sem_type_name_usa_expenses(financeiro, db_session):
    resultado = await financeiro.add_transaction(amount=10.0, source_text="algo")

    tx = db_session.get(Transaction, resultado["id"])
    assert tx.type == TransactionType.EXPENSES


async def test_total_balance_income_menos_expenses(financeiro, db_session):
    await financeiro.add_transaction(amount=100.0, source_text="salario", type_name="INCOME")
    await financeiro.add_transaction(amount=30.0, source_text="mercado", type_name="EXPENSES")

    resultado = await financeiro.total_balance()

    assert resultado == {"status": "ok", "amount": 70.0}


async def test_daily_balance_usa_fuso_sao_paulo_nao_utc(financeiro, db_session):
    # 2026-01-14 22:00 em São Paulo (UTC-3) = 2026-01-15 01:00 UTC. Um filtro que use
    # o fuso do servidor (UTC) cairia em 2026-01-15 — bug real já corrigido (ver TODO.md).
    ocorrido_em = datetime(2026, 1, 15, 1, 0, tzinfo=UTC)
    db_session.add(
        Transaction(
            amount=40, type=TransactionType.EXPENSES,
            occurred_at=ocorrido_em, source_text="depois das 22h em SP",
        )
    )
    db_session.commit()

    assert await financeiro.daily_balance(date_local="2026-01-14") == {
        "status": "ok", "balance_date": "2026-01-14", "total_balance": -40.0,
    }
    assert await financeiro.daily_balance(date_local="2026-01-15") == {
        "status": "ok", "balance_date": "2026-01-15", "total_balance": 0.0,
    }


async def test_query_transactions_com_intervalo_de_datas_retorna_cronologico(financeiro, db_session):
    await financeiro.add_transaction(amount=1, source_text="a", occurred_at="2026-01-01T12:00:00+00:00")
    await financeiro.add_transaction(amount=2, source_text="b", occurred_at="2026-01-02T12:00:00+00:00")

    resultado = await financeiro.query_transactions(date_from_local="2026-01-01", date_to_local="2026-01-02")

    assert [t["id"] for t in resultado["transactions"]] == [1, 2]


async def test_query_transactions_sem_intervalo_retorna_mais_recente_primeiro(financeiro, db_session):
    await financeiro.add_transaction(amount=1, source_text="a", occurred_at="2026-01-01T12:00:00+00:00")
    await financeiro.add_transaction(amount=2, source_text="b", occurred_at="2026-01-02T12:00:00+00:00")

    resultado = await financeiro.query_transactions()

    assert [t["id"] for t in resultado["transactions"]] == [2, 1]


async def test_query_transactions_filtra_por_source_text(financeiro, db_session):
    await financeiro.add_transaction(amount=1, source_text="mercado extra")
    await financeiro.add_transaction(amount=2, source_text="farmacia")

    resultado = await financeiro.query_transactions(source_text="mercado")

    assert resultado["total_records"] == 1
    assert resultado["transactions"][0]["amount"] == 1.0


async def test_update_transaction_sem_campos_retorna_erro(financeiro, db_session):
    resultado = await financeiro.update_transaction(id=1)

    assert resultado["status"] == "error"


async def test_update_transaction_sem_id_exige_match_text_e_date_local(financeiro, db_session):
    resultado = await financeiro.update_transaction(amount=10.0)

    assert resultado["status"] == "error"


async def test_update_transaction_amount_zero_e_aceito_como_valor_informado(financeiro, db_session):
    # amount=0.0 é "falsy" — a guarda de "nada pra atualizar" usava any() e recusava
    # a atualização mesmo o campo tendo sido informado (bug real, corrigido pra all(is None)).
    criada = await financeiro.add_transaction(amount=10.0, source_text="a corrigir")

    resultado = await financeiro.update_transaction(id=criada["id"], amount=0.0)

    assert resultado["status"] == "ok"
    assert resultado["rows_affected"] == 1
    assert db_session.get(Transaction, criada["id"]).amount == 0


async def test_update_transaction_id_inexistente_retorna_rows_affected_zero(financeiro, db_session):
    resultado = await financeiro.update_transaction(id=999, amount=10.0)

    assert resultado == {"status": "ok", "rows_affected": 0, "id": 999, "updated": None}


async def test_update_transaction_de_outro_usuario_e_tratada_como_nao_encontrada(financeiro, db_session):
    criada = await financeiro.add_transaction(amount=10.0, source_text="da vitima")

    with session_context(OUTRO_USUARIO):
        resultado = await financeiro.update_transaction(id=criada["id"], amount=999.0)

    assert resultado["rows_affected"] == 0
    assert db_session.get(Transaction, criada["id"]).amount == 10.0


async def test_update_transaction_localiza_por_match_text_ignorando_acento(financeiro, db_session):
    await financeiro.add_transaction(
        amount=15.0, source_text="pagamento açaí", type_name="EXPENSES",
        occurred_at="2026-02-01T12:00:00+00:00",
    )

    resultado = await financeiro.update_transaction(
        match_text="acai", date_local="2026-02-01", payment_method=PaymentType.PIX,
    )

    assert resultado["status"] == "ok"
    assert resultado["updated"]["payment_method"] == PaymentType.PIX
