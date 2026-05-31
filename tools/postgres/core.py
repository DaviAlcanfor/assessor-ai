from typing import List, Optional, Any
from langchain.tools import tool

from config.settings import DATABASE_URI
from config.decorators import log_tool
from config.logging import get_logger

from tools.response import Response
from tools.postgres.connection import get_conn
from tools.postgres.helpers import (
    resolve_type_id,
    get_category_id,
    local_date_filter_sql
)
from tools.postgres.schemas import (
    AddTransactionArgs,
    QueryTransactionArgs,
    UpdateTransactionArgs
)


logger = get_logger("pg_tools")


@log_tool
@tool("add_transaction", args_schema=AddTransactionArgs)
def add_transaction(
    amount: float,
    source_text: str,
    occurred_at: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
    category_name: Optional[str] = None,
) -> dict:
    """
    Insere uma transação financeira no banco de dados.

    O tipo pode ser informado por ID (type_id) ou nome (type_name).
    Aliases em português são aceitos: 'GASTO' → EXPENSES, 'GANHO' → INCOME.
    Se nenhum tipo for fornecido, assume EXPENSES por padrão.

    A categoria pode ser informada por ID (category_id) ou nome (category_name).
    Se occurred_at não for informado, usa o timestamp atual do servidor.
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                resolved_type_id = resolve_type_id(cur, type_id, type_name)
                if not resolved_type_id:
                    return Response.error("Tipo inválido (use type_id ou type_name: INCOME/EXPENSES/TRANSFER).")

                if not category_id:
                    category_id = get_category_id(cur, category_name)

                ts = occurred_at if occurred_at else "NOW()"
                cur.execute("""
                    INSERT INTO transactions
                        (amount, type, category_id, description, payment_method, occurred_at, source_text)
                    VALUES
                        (%s, %s, %s, %s, %s, %s::timestamptz, %s)
                    RETURNING id, occurred_at;
                """, (amount, resolved_type_id, category_id, description, payment_method, ts, source_text))

                new_id, occurred = cur.fetchone()
                conn.commit()

                logger.info("INSERT OK | id=%s amount=%.2f type_id=%s occurred_at=%s", new_id, amount, resolved_type_id, occurred)

                return Response.ok(id=new_id, occurred_at=str(occurred))

            except Exception as e:
                conn.rollback()
                logger.error("INSERT ERRO | %s", e)
                return Response.error(e)


@log_tool
@tool("total_balance")
def total_balance() -> dict:
    """Retorna o saldo total do usuário (INCOME - EXPENSES)."""

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT
                        (SUM(CASE WHEN type = 1 THEN amount ELSE 0 END) -
                         SUM(CASE WHEN type = 2 THEN amount ELSE 0 END)) AS total_balance
                    FROM transactions;
                """)
                result = cur.fetchone()
                balance = float(result[0]) if result and result[0] is not None else 0.0

                logger.info("QUERY OK | total_balance=%.2f", balance)

                return Response.ok(amount=balance)

            except Exception as e:
                logger.error("QUERY ERRO | total_balance | %s", e)
                return Response.error(e)


@log_tool
@tool("daily_balance")
def daily_balance(date_local: str) -> dict:
    """
    Retorna o saldo líquido do usuário em um dia específico (INCOME - EXPENSES).

    date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT
                        (SUM(CASE WHEN type = 1 THEN amount ELSE 0 END) -
                         SUM(CASE WHEN type = 2 THEN amount ELSE 0 END)) AS total_balance
                    FROM transactions
                    WHERE DATE(occurred_at) = DATE(%s)
                """, (date_local,))

                result = cur.fetchone()
                balance = float(result[0]) if result and result[0] is not None else 0.0

                logger.info("QUERY OK | daily_balance date=%s balance=%.2f", date_local, balance)

                return Response.ok(balance_date=date_local, total_balance=balance)

            except Exception as e:
                logger.error("QUERY ERRO | daily_balance | %s", e)
                return Response.error(e)


@log_tool
@tool("query_transactions", args_schema=QueryTransactionArgs)
def query_transactions(
    date_from_local: Optional[str] = None,
    date_to_local: Optional[str] = None,
    type_name: Optional[str] = None,
    source_text: Optional[str] = None,
) -> dict:
    """
    Consulta transações com filtros opcionais por data, tipo e texto.

    Quando date_from_local e date_to_local são informados juntos, retorna em ordem
    cronológica (ASC). Caso contrário, retorna as mais recentes primeiro (DESC).
    Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                base_query = """
                    SELECT id, amount, type, category_id, description, payment_method, occurred_at
                    FROM transactions
                    WHERE 1=1
                """
                params = []

                if date_from_local and date_to_local:
                    base_query += " AND DATE(occurred_at) BETWEEN %s AND %s"
                    params.extend([date_from_local, date_to_local])

                if type_name:
                    resolved_type_id = resolve_type_id(cur, None, type_name)
                    if resolved_type_id:
                        base_query += " AND type = %s"
                        params.append(resolved_type_id)

                if source_text:
                    base_query += " AND (source_text ILIKE %s OR description ILIKE %s)"
                    params.extend([f"%{source_text}%", f"%{source_text}%"])

                base_query += " ORDER BY occurred_at ASC" if (date_from_local and date_to_local) else " ORDER BY occurred_at DESC"

                cur.execute(base_query, params)
                rows = cur.fetchall()

                transactions = [
                    {
                        "id":             row[0],
                        "amount":         float(row[1]),
                        "type":           row[2],
                        "category_id":    row[3],
                        "description":    row[4],
                        "payment_method": row[5],
                        "occurred_at":    str(row[6]),
                    }
                    for row in rows
                ]

                logger.info("QUERY OK | query_transactions | total_records=%s", len(transactions))

                return Response.ok(total_records=len(transactions), transactions=transactions)

            except Exception as e:
                logger.error("QUERY ERRO | query_transactions | %s", e)
                return Response.error(e)


@log_tool
@tool("update_transaction", args_schema=UpdateTransactionArgs)
def update_transaction(
    id: Optional[int] = None,
    match_text: Optional[str] = None,
    date_local: Optional[str] = None,
    amount: Optional[float] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict:
    """
    Atualiza campos de uma transação existente.

    Localização por ID direto (id) ou por texto + data (match_text + date_local).
    Quando localizada por texto, atualiza a ocorrência mais recente que combine.
    Pelo menos um campo de atualização deve ser fornecido.
    Retorna o registro atualizado completo após o commit.
    """

    if not any([amount, type_id, type_name, category_id, category_name, description, payment_method, occurred_at]):
        return Response.error("Nada para atualizar: forneça pelo menos um campo.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                target_id = id
                if target_id is None:
                    if not match_text or not date_local:
                        return Response.error("Sem 'id': informe match_text E date_local para localizar o registro.")

                    cur.execute(
                        f"""
                        SELECT t.id FROM transactions t
                        WHERE (t.source_text ILIKE %s OR t.description ILIKE %s)
                          AND {local_date_filter_sql("t.occurred_at")}
                        ORDER BY t.occurred_at DESC
                        LIMIT 1;
                        """,
                        (f"%{match_text}%", f"%{match_text}%", date_local)
                    )
                    row = cur.fetchone()
                    if not row:
                        return Response.error("Nenhuma transação encontrada para os filtros fornecidos.")
                    target_id = row[0]

                resolved_type_id     = resolve_type_id(cur, type_id, type_name) if (type_id or type_name) else None
                resolved_category_id = category_id
                if category_name and not category_id:
                    resolved_category_id = get_category_id(cur, category_name)

                sets: List[str] = []
                params: List[Any] = []

                if amount           is not None: sets.append("amount = %s");                    params.append(amount)
                if resolved_type_id is not None: sets.append("type = %s");                      params.append(resolved_type_id)
                if resolved_category_id is not None: sets.append("category_id = %s");           params.append(resolved_category_id)
                if description      is not None: sets.append("description = %s");               params.append(description)
                if payment_method   is not None: sets.append("payment_method = %s");            params.append(payment_method)
                if occurred_at      is not None: sets.append("occurred_at = %s::timestamptz");  params.append(occurred_at)

                if not sets:
                    return Response.error("Nenhum campo válido para atualizar.")

                params.append(target_id)
                cur.execute(f"UPDATE transactions SET {', '.join(sets)} WHERE id = %s;", params)
                rows_affected = cur.rowcount
                conn.commit()

                cur.execute("""
                    SELECT t.id, t.occurred_at, t.amount, tt.type, c.name, t.description, t.payment_method, t.source_text
                    FROM transactions t
                    JOIN transaction_types tt ON tt.id = t.type
                    LEFT JOIN categories c ON c.id = t.category_id
                    WHERE t.id = %s;
                """, (target_id,))

                row = cur.fetchone()
                updated = {
                    "id": row[0], "occurred_at": str(row[1]), "amount": float(row[2]),
                    "type": row[3], "category": row[4], "description": row[5],
                    "payment_method": row[6], "source_text": row[7],
                } if row else None

                logger.info("UPDATE OK | id=%s rows_affected=%s", target_id, rows_affected)

                return Response.ok(
                    rows_affected=rows_affected, 
                    id=target_id, 
                    updated=updated
                )

            except Exception as e:
                conn.rollback()
                logger.error("UPDATE ERRO | id=%s | %s", target_id, e)
                return Response.error(e)


__all__ = [
    "add_transaction", 
    "daily_balance", 
    "total_balance", 
    "query_transactions", 
    "update_transaction",
]