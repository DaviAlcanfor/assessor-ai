import psycopg2
from typing import List, Optional, Any
from langchain.tools import tool

from tools.response import Response
from config import DATABASE_URI
from tools.schemas import (
    AddTransactionArgs,
    QueryTransactionArgs, 
    UpdateTransactionArgs
)


# TODO totalmente mutável para uma pool de conexoes
def get_conn():
    return psycopg2.connect(DATABASE_URI)


# Garante que o campo type da tabela transactions receba um id válido (1=INCOME, 2=EXPENSES, 3=TRANSFER
def _resolve_type_id(cur, type_id: Optional[int], type_name: Optional[str]) -> Optional[int]:

    TYPE_ALIASES = {
        "INCOME":["GANHO", "RENDA", "ENTRADA"],
        "EXPENSES":["DESPESA", "GASTO"],
        "TRANSFER":["MANDEI", "TRANSFER", "ENVIO"],
    }
    
    if type_name:
        t = type_name.strip().upper()
        
        if t == "EXPENSE":
            t = "EXPENSES"
            
        for main_type, aliases in TYPE_ALIASES.items():
            if t == main_type or t in aliases:
                t = main_type
                break
                        
        cur.execute("SELECT id FROM transaction_types WHERE UPPER(type)=%s LIMIT 1;", (t,))
        row = cur.fetchone()
        return row[0] if row else None
    
    if type_id:
        return int(type_id)
    return 2 # default: EXPENSES

def _get_category_id(cur, category_name: Optional[str]) -> Optional[int]:
    if not category_name:
        return None
    cur.execute(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(%s) LIMIT 1;",
        (category_name,)
    )
    row = cur.fetchone()
    return row[0] if row else None

def _local_date_filter_sql(field: str = "occurred_at") -> str:
    """
    Retorna um trecho SQL para filtragem por dia local em America/Sao_Paulo.
    Ex.: (occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s::date
    """
    return f"(({field} AT TIME ZONE 'America/Sao_Paulo')::date = %s::date)"


# Tool: add_transaction
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
    """Insere uma transação financeira no banco de dados Postgres.""" # docstring obrigatório da @tools do langchain (estranho, mas legal né?)
   
    with get_conn() as conn:
        with conn.cursor() as cur:
    
            try:
                resolved_type_id = _resolve_type_id(cur, type_id, type_name)
                if not resolved_type_id:
                    return Response.error("Tipo inválido (use type_id ou type_name: INCOME/EXPENSES/TRANSFER).")
                    
                if not category_id:
                    category_id = _get_category_id(cur, category_name)
                    
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
                
                
                return Response.ok(
                    id=new_id, 
                    occurred_at=str(occurred)
                )

            except Exception as e:
                conn.rollback()
                return Response.error(e)


@tool("total_balance")
def total_balance() -> dict:
    """
    Retorna o saldo total do usuário (INCOME - EXPENSES)
    """

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
                
                return Response.ok(amount=float(result[0]) if result and result[0] is not None else 0)
            except Exception as e:
                return Response.error(e)



@tool("daily_balance")
def daily_balance(date_local: str) -> dict:
    """
    Retorna o saldo total do usuário (INCOME - EXPENSES) em um dia específico.
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
                
                return Response.ok(
                    balance_date=date_local,
                    total_balance=float(result[0]) if result and result[0] is not None else 0
                )

            except Exception as e:
                return Response.error(e)
                
@tool("query_transactions", args_schema=QueryTransactionArgs)
def query_transactions(
        date_from_local: Optional[str] = None, 
        date_to_local: Optional[str] = None,
        type_name: Optional[str] = None,
        source_text: Optional[str] = None
    ) -> dict:
    """
    Consulta transações com filtros por texto (source_text/description), tipo e datas locais (America/Sao_Paulo).
    Os dados devem vir na seguinte ordem:
    - Intervalo (date_from_local/date_to_local): ASC (cronológico).
    - Caso contrário: DESC (mais recentes primeiro).
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                base_query = """
                    SELECT 
                        id, 
                        amount, 
                        type, 
                        category_id, 
                        description, 
                        payment_method, 
                        occurred_at
                    FROM transactions
                    WHERE 1=1
                """
                params = []
                
                if date_from_local and date_to_local:
                    base_query += " AND DATE(occurred_at) BETWEEN %s AND %s"
                    params.extend([date_from_local, date_to_local])
                
                if type_name:
                    resolved_type_id = _resolve_type_id(cur, None, type_name)
                    if resolved_type_id:
                        base_query += " AND type = %s"
                        params.append(resolved_type_id)
                
                if source_text:
                    base_query += " AND (source_text ILIKE %s OR description ILIKE %s)"
                    params.extend([f"%{source_text}%", f"%{source_text}%"])
                
                if date_from_local and date_to_local:
                    base_query += " ORDER BY occurred_at ASC"
                else:
                    base_query += " ORDER BY occurred_at DESC"
                
                cur.execute(base_query, params)
                rows = cur.fetchall()
                
                transactions = [
                    {
                        "id": row[0],
                        "amount": float(row[1]),
                        "type": row[2],
                        "category_id": row[3],
                        "description": row[4],
                        "payment_method": row[5],
                        "occurred_at": str(row[6]),
                    }
                    for row in rows
                ]
                
                return Response.ok(
                    total_records=len(transactions),
                    transactions=transactions
                )

            except Exception as e:
                return Response.error(e)
                

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
    Atualiza uma transação existente.
    Estratégias:
      - Se 'id' for informado: atualiza diretamente por ID.
      - Caso contrário: localiza a transação mais recente que combine (match_text em source_text/description)
        E (date_local em America/Sao_Paulo), então atualiza.
    Retorna: status, rows_affected, id, e o registro atualizado.
    """
    if not any([amount, type_id, type_name, category_id, category_name, description, payment_method, occurred_at]):
        return Response.error("Nada para atualizar: forneça pelo menos um campo (amount, type, category, description, payment_method, occurred_at).")

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                # Resolve target_id
                target_id = id
                if target_id is None:
                    if not match_text or not date_local:
                        return Response.error("Sem 'id': informe match_text E date_local para localizar o registro.")

                    # Buscar o mais recente no dia local informado que combine o texto
                    cur.execute(
                        f"""
                        SELECT t.id
                        FROM transactions t
                        WHERE (t.source_text ILIKE %s OR t.description ILIKE %s)
                          AND {_local_date_filter_sql("t.occurred_at")}
                        ORDER BY t.occurred_at DESC
                        LIMIT 1;
                        """,
                        (f"%{match_text}%", f"%{match_text}%", date_local)
                    )
                    row = cur.fetchone()
                    if not row:
                        return Response.error("Nenhuma transação encontrada para os filtros fornecidos.")
                    target_id = row[0]

                # Resolver type_id / category_id a partir de nomes, se fornecidos
                resolved_type_id = _resolve_type_id(cur, type_id, type_name) if (type_id or type_name) else None
                resolved_category_id = category_id
                if category_name and not category_id:
                    resolved_category_id = _get_category_id(cur, category_name)

                # Montar SET dinâmico
                sets = []
                params: List[Any] = []
                if amount is not None:
                    sets.append("amount = %s")
                    params.append(amount)
                if resolved_type_id is not None:
                    sets.append("type = %s")
                    params.append(resolved_type_id)
                if resolved_category_id is not None:
                    sets.append("category_id = %s")
                    params.append(resolved_category_id)
                if description is not None:
                    sets.append("description = %s")
                    params.append(description)
                if payment_method is not None:
                    sets.append("payment_method = %s")
                    params.append(payment_method)
                if occurred_at is not None:
                    sets.append("occurred_at = %s::timestamptz")
                    params.append(occurred_at)

                if not sets:
                    return Response.error("Nenhum campo válido para atualizar.")

                params.append(target_id)

                cur.execute(
                    f"UPDATE transactions SET {', '.join(sets)} WHERE id = %s;",
                    params
                )
                rows_affected = cur.rowcount
                conn.commit()

                # Retornar o registro atualizado
                cur.execute(
                    """
                    SELECT
                      t.id, t.occurred_at, t.amount, tt.type AS type_name,
                      c.name AS category_name, t.description, t.payment_method, t.source_text
                    FROM transactions t
                    JOIN transaction_types tt ON tt.id = t.type
                    LEFT JOIN categories c ON c.id = t.category_id
                    WHERE t.id = %s;
                    """,
                    (target_id,)
                )
                row = cur.fetchone()
                updated = None
                if row:
                    updated = {
                        "id": row[0],
                        "occurred_at": str(row[1]),
                        "amount": float(row[2]),
                        "type": row[3],
                        "category": row[4],
                        "description": row[5],
                        "payment_method": row[6],
                        "source_text": row[7],
                    }

                return Response.ok(
                    rows_affected=rows_affected,
                    id=target_id,
                    updated=updated
                )

            except Exception as e:
                conn.rollback()
                return Response.error(e)


TOOLS = [add_transaction, daily_balance, total_balance, query_transactions, update_transaction]
