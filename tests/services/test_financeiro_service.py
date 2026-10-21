import pytest

from app.domain.errors import DadosInvalidos
from app.domain.models.financeiro import TransactionType
from app.services.financeiro_service import resolve_transaction_type


@pytest.mark.parametrize("type_name", [None, ""])
def test_sem_tipo_usa_expenses(type_name):
    assert resolve_transaction_type(type_name) == TransactionType.EXPENSES


@pytest.mark.parametrize(
    ("type_name", "esperado"),
    [
        ("INCOME", TransactionType.INCOME),
        ("  income ", TransactionType.INCOME),
        ("EXPENSES", TransactionType.EXPENSES),
        ("transfer", TransactionType.TRANSFER),
    ],
)
def test_aceita_os_tres_valores_sem_diferenciar_caixa_nem_espaco(type_name, esperado):
    assert resolve_transaction_type(type_name) == esperado


@pytest.mark.parametrize("type_name", ["GASTO", "GANHO", "despesa", "MANDEI"])
def test_alias_nao_existe_mais_o_schema_da_tool_ja_restringe_o_llm(type_name):
    with pytest.raises(DadosInvalidos, match="INCOME, EXPENSES, TRANSFER"):
        resolve_transaction_type(type_name)
