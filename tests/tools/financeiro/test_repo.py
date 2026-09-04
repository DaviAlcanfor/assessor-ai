from datetime import UTC, datetime
from uuid import UUID

from assessor_ai.graph.tools.financeiro.models import (
    PaymentType,
    Transaction,
    TransactionType,
)
from assessor_ai.infra.postgres import reset_current_user, set_current_user

OUTRO_USUARIO = UUID("11111111-1111-1111-1111-111111111111")


def test_add_transaction_resolve_categoria_por_nome(financeiro, db_session, categoria):
    resultado = financeiro.add_transaction(amount=50.0, source_text="mercado", category_name="Mercado")

    assert resultado["status"] == "ok"
    tx = db_session.get(Transaction, resultado["id"])
    assert tx.category_id == categoria.id


def test_add_transaction_sem_type_name_usa_expenses(financeiro, db_session):
    resultado = financeiro.add_transaction(amount=10.0, source_text="algo")

    tx = db_session.get(Transaction, resultado["id"])
    assert tx.type == TransactionType.EXPENSES


def test_total_balance_income_menos_expenses(financeiro, db_session):
    financeiro.add_transaction(amount=100.0, source_text="salario", type_name="INCOME")
    financeiro.add_transaction(amount=30.0, source_text="mercado", type_name="GASTO")

    resultado = financeiro.total_balance()

    assert resultado == {"status": "ok", "amount": 70.0}


def test_daily_balance_usa_fuso_sao_paulo_nao_utc(financeiro, db_session):
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

    assert financeiro.daily_balance(date_local="2026-01-14") == {
        "status": "ok", "balance_date": "2026-01-14", "total_balance": -40.0,
    }
    assert financeiro.daily_balance(date_local="2026-01-15") == {
        "status": "ok", "balance_date": "2026-01-15", "total_balance": 0.0,
    }


def test_query_transactions_com_intervalo_de_datas_retorna_cronologico(financeiro, db_session):
    financeiro.add_transaction(amount=1, source_text="a", occurred_at="2026-01-01T12:00:00+00:00")
    financeiro.add_transaction(amount=2, source_text="b", occurred_at="2026-01-02T12:00:00+00:00")

    resultado = financeiro.query_transactions(date_from_local="2026-01-01", date_to_local="2026-01-02")

    assert [t["id"] for t in resultado["transactions"]] == [1, 2]


def test_query_transactions_sem_intervalo_retorna_mais_recente_primeiro(financeiro, db_session):
    financeiro.add_transaction(amount=1, source_text="a", occurred_at="2026-01-01T12:00:00+00:00")
    financeiro.add_transaction(amount=2, source_text="b", occurred_at="2026-01-02T12:00:00+00:00")

    resultado = financeiro.query_transactions()

    assert [t["id"] for t in resultado["transactions"]] == [2, 1]


def test_query_transactions_filtra_por_source_text(financeiro, db_session):
    financeiro.add_transaction(amount=1, source_text="mercado extra")
    financeiro.add_transaction(amount=2, source_text="farmacia")

    resultado = financeiro.query_transactions(source_text="mercado")

    assert resultado["total_records"] == 1
    assert resultado["transactions"][0]["amount"] == 1.0


def test_update_transaction_sem_campos_retorna_erro(financeiro, db_session):
    resultado = financeiro.update_transaction(id=1)

    assert resultado["status"] == "error"


def test_update_transaction_sem_id_exige_match_text_e_date_local(financeiro, db_session):
    resultado = financeiro.update_transaction(amount=10.0)

    assert resultado["status"] == "error"


def test_update_transaction_id_inexistente_retorna_rows_affected_zero(financeiro, db_session):
    resultado = financeiro.update_transaction(id=999, amount=10.0)

    assert resultado == {"status": "ok", "rows_affected": 0, "id": 999, "updated": None}


def test_update_transaction_de_outro_usuario_e_tratada_como_nao_encontrada(financeiro, db_session):
    criada = financeiro.add_transaction(amount=10.0, source_text="da vitima")

    token = set_current_user(OUTRO_USUARIO)
    try:
        resultado = financeiro.update_transaction(id=criada["id"], amount=999.0)
    finally:
        reset_current_user(token)

    assert resultado["rows_affected"] == 0
    assert db_session.get(Transaction, criada["id"]).amount == 10.0


def test_update_transaction_localiza_por_match_text_ignorando_acento(financeiro, db_session):
    financeiro.add_transaction(
        amount=15.0, source_text="pagamento açaí", type_name="GASTO",
        occurred_at="2026-02-01T12:00:00+00:00",
    )

    resultado = financeiro.update_transaction(
        match_text="acai", date_local="2026-02-01", payment_method=PaymentType.PIX,
    )

    assert resultado["status"] == "ok"
    assert resultado["updated"]["payment_method"] == PaymentType.PIX
