from datetime import UTC, datetime

from langchain.tools import tool
from sqlalchemy import case, func, or_, select

from config.decorators import log_tool
from config.logging import get_logger
from tools.postgres.connection import get_session
from tools.postgres.financeiro.schemas import (
    AddTransactionArgs,
    QueryTransactionArgs,
    UpdateTransactionArgs,
)
from tools.postgres.helpers import (
    get_category_id,
    local_date_filter,
    resolve_transaction_type,
)
from tools.postgres.models import PaymentType, Transaction, TransactionType
from tools.response import Response

logger = get_logger("pg_tools")



@tool("add_transaction", args_schema=AddTransactionArgs)
@log_tool
def add_transaction(
    amount: float,
    source_text: str,
    occurred_at: str | None = None,
    type_name: str | None = None,
    category_id: int | None = None,
    description: str | None = None,
    payment_method: PaymentType | None = None,
    category_name: str | None = None,
) -> dict:
    """
    Insere uma transação financeira no banco de dados.

    O tipo é informado por nome (type_name). Aliases em português são aceitos:
    'GASTO' → EXPENSES, 'GANHO' → INCOME. Se nenhum tipo for fornecido, assume
    EXPENSES por padrão.

    A categoria pode ser informada por ID (category_id) ou nome (category_name).
    Se occurred_at não for informado, usa o timestamp atual do servidor.
    """

    with get_session() as session:
        try:
            resolved_type = resolve_transaction_type(type_name)

            if not category_id:
                category_id = get_category_id(session, category_name)

            tx = Transaction(
                amount=amount,
                type=resolved_type,
                category_id=category_id,
                description=description,
                payment_method=payment_method,
                occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(UTC),
                source_text=source_text,
            )
            session.add(tx)
            session.flush()

            logger.info("INSERT OK | id=%s amount=%.2f type=%s occurred_at=%s", tx.id, amount, resolved_type, tx.occurred_at)

            return Response.ok(id=tx.id, occurred_at=str(tx.occurred_at))

        except Exception as e:
            logger.error("INSERT ERRO | %s", e)
            return Response.error(e)


@tool("total_balance")
@log_tool
def total_balance() -> dict:
    """Retorna o saldo total do usuário (INCOME - EXPENSES)."""

    with get_session() as session:
        try:
            result = session.scalar(
                select(
                    func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0))
                    - func.sum(case((Transaction.type == TransactionType.EXPENSES, Transaction.amount), else_=0))
                )
            )
            balance = float(result) if result is not None else 0.0

            logger.info("QUERY OK | total_balance=%.2f", balance)

            return Response.ok(amount=balance)

        except Exception as e:
            logger.error("QUERY ERRO | total_balance | %s", e)
            return Response.error(e)


@tool("daily_balance")
@log_tool
def daily_balance(date_local: str) -> dict:
    """
    Retorna o saldo líquido do usuário em um dia específico (INCOME - EXPENSES).

    date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
    """

    with get_session() as session:
        try:
            result = session.scalar(
                select(
                    func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0))
                    - func.sum(case((Transaction.type == TransactionType.EXPENSES, Transaction.amount), else_=0))
                )
                .where(func.date(Transaction.occurred_at) == func.date(date_local))
            )
            balance = float(result) if result is not None else 0.0

            logger.info("QUERY OK | daily_balance date=%s balance=%.2f", date_local, balance)

            return Response.ok(balance_date=date_local, total_balance=balance)

        except Exception as e:
            logger.error("QUERY ERRO | daily_balance | %s", e)
            return Response.error(e)


@tool("query_transactions", args_schema=QueryTransactionArgs)
@log_tool
def query_transactions(
    date_from_local: str | None = None,
    date_to_local: str | None = None,
    type_name: str | None = None,
    source_text: str | None = None,
) -> dict:
    """
    Consulta transações com filtros opcionais por data, tipo e texto.

    Quando date_from_local e date_to_local são informados juntos, retorna em ordem
    cronológica (ASC). Caso contrário, retorna as mais recentes primeiro (DESC).
    Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
    """

    with get_session() as session:
        try:
            stmt = select(Transaction)

            if date_from_local and date_to_local:
                stmt = stmt.where(func.date(Transaction.occurred_at).between(date_from_local, date_to_local))
                stmt = stmt.order_by(Transaction.occurred_at.asc())
            else:
                stmt = stmt.order_by(Transaction.occurred_at.desc())

            if type_name:
                stmt = stmt.where(Transaction.type == resolve_transaction_type(type_name))

            if source_text:
                like = f"%{source_text}%"
                stmt = stmt.where(or_(Transaction.source_text.ilike(like), Transaction.description.ilike(like)))

            rows = session.scalars(stmt).all()

            transactions = [
                {
                    "id":             t.id,
                    "amount":         float(t.amount),
                    "type":           t.type,
                    "category_id":    t.category_id,
                    "description":    t.description,
                    "payment_method": t.payment_method,
                    "occurred_at":    str(t.occurred_at),
                }
                for t in rows
            ]

            logger.info("QUERY OK | query_transactions | total_records=%s", len(transactions))

            return Response.ok(total_records=len(transactions), transactions=transactions)

        except Exception as e:
            logger.error("QUERY ERRO | query_transactions | %s", e)
            return Response.error(e)


@tool("update_transaction", args_schema=UpdateTransactionArgs)
@log_tool
def update_transaction(
    id: int | None = None,
    match_text: str | None = None,
    date_local: str | None = None,
    amount: float | None = None,
    type_name: str | None = None,
    category_id: int | None = None,
    category_name: str | None = None,
    description: str | None = None,
    payment_method: PaymentType | None = None,
    occurred_at: str | None = None,
) -> dict:
    """
    Atualiza campos de uma transação existente.

    Localização por ID direto (id) ou por texto + data (match_text + date_local).
    Quando localizada por texto, atualiza a ocorrência mais recente que combine.
    Pelo menos um campo de atualização deve ser fornecido.
    Retorna o registro atualizado completo após o commit.
    """

    if not any([amount, type_name, category_id, category_name, description, payment_method, occurred_at]):
        return Response.error("Nada para atualizar: forneça pelo menos um campo.")

    target_id = id

    with get_session() as session:
        try:
            if target_id is None:
                if not match_text or not date_local:
                    return Response.error("Sem 'id': informe match_text E date_local para localizar o registro.")

                target_id = session.scalar(
                    select(Transaction.id)
                    .where(
                        or_(
                            func.unaccent(Transaction.source_text).ilike(func.unaccent(f"%{match_text}%")),
                            func.unaccent(Transaction.description).ilike(func.unaccent(f"%{match_text}%")),
                        ),
                        local_date_filter(Transaction.occurred_at, date_local),
                    )
                    .order_by(Transaction.occurred_at.desc())
                    .limit(1)
                )
                if not target_id:
                    return Response.error("Nenhuma transação encontrada para os filtros fornecidos.")

            tx = session.get(Transaction, target_id)
            if tx is None:
                return Response.ok(rows_affected=0, id=target_id, updated=None)

            resolved_type         = resolve_transaction_type(type_name) if type_name else None
            resolved_category_id = category_id
            if category_name and not category_id:
                resolved_category_id = get_category_id(session, category_name)

            if amount is not None:           tx.amount = amount
            if resolved_type is not None:    tx.type = resolved_type
            if resolved_category_id is not None: tx.category_id = resolved_category_id
            if description is not None:      tx.description = description
            if payment_method is not None:   tx.payment_method = payment_method
            if occurred_at is not None:      tx.occurred_at = datetime.fromisoformat(occurred_at)

            session.flush()

            updated = {
                "id": tx.id, "occurred_at": str(tx.occurred_at), "amount": float(tx.amount),
                "type": tx.type, "category": tx.category.name if tx.category else None,
                "description": tx.description, "payment_method": tx.payment_method, "source_text": tx.source_text,
            }

            logger.info("UPDATE OK | id=%s rows_affected=1", target_id)

            return Response.ok(
                rows_affected=1,
                id=target_id,
                updated=updated
            )

        except Exception as e:
            logger.error("UPDATE ERRO | id=%s | %s", target_id, e)
            return Response.error(e)


__all__ = [
    "add_transaction",
    "daily_balance",
    "query_transactions",
    "total_balance",
    "update_transaction",
]
