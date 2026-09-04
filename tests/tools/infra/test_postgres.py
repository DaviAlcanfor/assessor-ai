import pytest
from sqlalchemy import column

from assessor_ai.graph.tools.financeiro.models import TransactionType
from assessor_ai.graph.tools.financeiro.repo import resolve_transaction_type
from assessor_ai.infra.postgres import (
    local_date,
    local_date_filter,
    local_date_range_filter,
)


@pytest.mark.parametrize("type_name", [None, ""])
def test_resolve_transaction_type_sem_argumento_usa_expenses(type_name):
    assert resolve_transaction_type(type_name) == TransactionType.EXPENSES


@pytest.mark.parametrize(
    "type_name",
    ["INCOME", "income", "  Income  ", "GANHO", "renda", "ENTRADA"],
)
def test_resolve_transaction_type_aliases_de_income(type_name):
    assert resolve_transaction_type(type_name) == TransactionType.INCOME


@pytest.mark.parametrize("type_name", ["EXPENSES", "DESPESA", "gasto", "EXPENSE"])
def test_resolve_transaction_type_aliases_de_expenses(type_name):
    assert resolve_transaction_type(type_name) == TransactionType.EXPENSES


@pytest.mark.parametrize("type_name", ["TRANSFER", "MANDEI", "envio"])
def test_resolve_transaction_type_aliases_de_transfer(type_name):
    assert resolve_transaction_type(type_name) == TransactionType.TRANSFER


def test_resolve_transaction_type_desconhecido_usa_expenses():
    assert resolve_transaction_type("chocolate") == TransactionType.EXPENSES


def test_local_date_aplica_timezone_sao_paulo():
    expressao = local_date(column("occurred_at"))

    assert str(expressao) == "date(timezone(:timezone_1, occurred_at))"


def test_local_date_filter_compara_com_data_local():
    expressao = local_date_filter(column("occurred_at"), "2026-01-01")
    sql = str(expressao.compile(compile_kwargs={"literal_binds": True}))

    assert sql == "date(timezone('America/Sao_Paulo', occurred_at)) = '2026-01-01'"


def test_local_date_range_filter_usa_between():
    expressao = local_date_range_filter(
        column("occurred_at"), "2026-01-01", "2026-01-31"
    )
    sql = str(expressao.compile(compile_kwargs={"literal_binds": True}))

    assert sql == (
        "date(timezone('America/Sao_Paulo', occurred_at)) "
        "BETWEEN '2026-01-01' AND '2026-01-31'"
    )
