
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from assessor_ai.tools.postgres.models import Category, TransactionType

_TYPE_ALIASES: dict[str, list[str]] = {
    "INCOME":   ["GANHO", "RENDA", "ENTRADA"],
    "EXPENSES": ["DESPESA", "GASTO", "EXPENSE"],
    "TRANSFER": ["MANDEI", "TRANSFER", "ENVIO"],
}


def resolve_transaction_type(type_name: str | None) -> TransactionType:
    """
    Resolve o tipo de transação a partir de um nome livre (aceita aliases em
    português, ex: "GASTO" → EXPENSES). Sem argumento, retorna o tipo padrão
    (EXPENSES). Puramente em Python — não depende mais de lookup em tabela.
    """

    if not type_name:
        return TransactionType.EXPENSES

    t = type_name.strip().upper()

    for main_type, aliases in _TYPE_ALIASES.items():
        if t == main_type or t in aliases:
            return TransactionType(main_type)

    return TransactionType.EXPENSES


def get_category_id(session: Session, category_name: str | None) -> int | None:
    """
    Busca o ID de uma categoria pelo nome, com comparação case-insensitive.

    Retorna None se category_name não for fornecido ou não encontrado.
    """

    if not category_name:
        return None

    return session.scalar(
        select(Category.id).where(func.lower(Category.name) == category_name.lower())
    )


def local_date(column):
    """
    Expressão de data local (America/Sao_Paulo) a partir de uma coluna timestamptz.

    Equivalente a: (column AT TIME ZONE 'America/Sao_Paulo')::date
    """

    return func.date(func.timezone("America/Sao_Paulo", column))


def local_date_filter(column, date_local: str) -> ColumnElement[bool]:
    """Expressão booleana pra filtrar registros por uma data local específica."""

    return local_date(column) == date_local


def local_date_range_filter(column, date_from_local: str, date_to_local: str) -> ColumnElement[bool]:
    """Expressão booleana pra filtrar registros por um intervalo de datas locais."""

    return local_date(column).between(date_from_local, date_to_local)


__all__ = [
    "get_category_id",
    "local_date",
    "local_date_filter",
    "local_date_range_filter",
    "resolve_transaction_type",
]
