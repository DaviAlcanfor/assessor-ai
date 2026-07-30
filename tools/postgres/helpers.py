from typing import Optional

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from tools.postgres.models import Category, TransactionType


_TYPE_ALIASES: dict[str, list[str]] = {
    "INCOME":   ["GANHO", "RENDA", "ENTRADA"],
    "EXPENSES": ["DESPESA", "GASTO"],
    "TRANSFER": ["MANDEI", "TRANSFER", "ENVIO"],
}

_DEFAULT_TYPE_ID = 2  # EXPENSES


def resolve_type_id(
    session:   Session,
    type_id:   Optional[int],
    type_name: Optional[str],
) -> Optional[int]:
    """
    Resolve o ID do tipo de transação a partir de um nome ou ID direto.

    Aceita aliases em português (ex: "GASTO" → EXPENSES).
    Se nenhum argumento for fornecido, retorna o tipo padrão (EXPENSES).
    """

    if type_name:
        t = type_name.strip().upper()

        if t == "EXPENSE":
            t = "EXPENSES"

        for main_type, aliases in _TYPE_ALIASES.items():
            if t == main_type or t in aliases:
                t = main_type
                break

        return session.scalar(
            select(TransactionType.id).where(func.upper(TransactionType.type) == t)
        )

    if type_id:
        return int(type_id)

    return _DEFAULT_TYPE_ID


def get_category_id(session: Session, category_name: Optional[str]) -> Optional[int]:
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
    "resolve_type_id",
    "get_category_id",
    "local_date",
    "local_date_filter",
    "local_date_range_filter",
]
