from typing import Optional


_TYPE_ALIASES: dict[str, list[str]] = {
    "INCOME":   ["GANHO", "RENDA", "ENTRADA"],
    "EXPENSES": ["DESPESA", "GASTO"],
    "TRANSFER": ["MANDEI", "TRANSFER", "ENVIO"],
}

_DEFAULT_TYPE_ID = 2  # EXPENSES


def resolve_type_id(
    cur,
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

        cur.execute("SELECT id FROM transaction_types WHERE UPPER(type)=%s LIMIT 1;", (t,))
        row = cur.fetchone()
        return row[0] if row else None

    if type_id:
        return int(type_id)

    return _DEFAULT_TYPE_ID


def get_category_id(cur, category_name: Optional[str]) -> Optional[int]:
    """
    Busca o ID de uma categoria pelo nome, com comparação case-insensitive.

    Retorna None se category_name não for fornecido ou não encontrado.
    """

    if not category_name:
        return None

    cur.execute(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(%s) LIMIT 1;",
        (category_name,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def local_date_filter_sql(field: str = "occurred_at") -> str:
    """
    Gera um trecho SQL para filtrar registros por data local (America/Sao_Paulo).

    Exemplo de saída:
        ((occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s::date)
    """
    
    return f"(({field} AT TIME ZONE 'America/Sao_Paulo')::date = %s::date)"



__all__ = [
    "resolve_type_id",
    "get_category_id",
    "local_date_filter_sql",
]