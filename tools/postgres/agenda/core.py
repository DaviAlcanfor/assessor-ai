from typing import Optional, Any, List
from langchain.tools import tool

from config.decorators import log_tool
from config.logging import get_logger

from tools.response import Response
from tools.postgres.connection import get_conn
from tools.postgres.agenda.schemas import (
    AddEventArgs,
    QueryEventArgs,
    UpdateEventArgs,
)


logger = get_logger("pg_events")


@tool("add_event", args_schema=AddEventArgs)
@log_tool
def add_event(
    title: str,
    start_time: str,
    source_text: str,
    notes: str,
    end_time: Optional[str] = None,
    location: Optional[str] = None,
) -> dict:
    """
    Insere um evento na agenda do usuário.

    start_time e end_time devem estar no formato ISO 8601.
    recorded_at é preenchido automaticamente com NOW().
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO events
                        (title, start_time, end_time, location, notes, source_text, recorded_at)
                    VALUES
                        (%s, %s::timestamptz, %s::timestamptz, %s, %s, %s, NOW())
                    RETURNING id, recorded_at;
                """, (title, start_time, end_time, location, notes, source_text))

                new_id, recorded_at = cur.fetchone()
                conn.commit()

                logger.info("INSERT OK | id=%s title=%s start_time=%s", new_id, title, start_time)

                return Response.ok(id=new_id, recorded_at=str(recorded_at))

            except Exception as e:
                conn.rollback()
                logger.error("INSERT ERRO | %s", e)
                return Response.error(e)


@tool("query_daily_events")
@log_tool
def query_daily_events(date_local: str) -> dict:
    """
    Retorna todos os eventos de um dia específico.

    date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT id, title, start_time, end_time, location, notes
                    FROM events
                    WHERE DATE(start_time AT TIME ZONE 'America/Sao_Paulo') = %s
                    ORDER BY start_time ASC;
                """, (date_local,))

                rows = cur.fetchall()
                events = [
                    {
                        "id":         row[0],
                        "title":      row[1],
                        "start_time": str(row[2]),
                        "end_time":   str(row[3]) if row[3] else None,
                        "location":   row[4],
                        "notes":      row[5],
                    }
                    for row in rows
                ]

                logger.info("QUERY OK | query_daily_events date=%s total=%s", date_local, len(events))

                return Response.ok(date=date_local, total_records=len(events), events=events)

            except Exception as e:
                logger.error("QUERY ERRO | query_daily_events | %s", e)
                return Response.error(e)


@tool("query_events", args_schema=QueryEventArgs)
@log_tool
def query_events(
    date_from_local: Optional[str] = None,
    date_to_local: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """
    Consulta eventos com filtros opcionais por período e título.

    Quando date_from_local e date_to_local são informados juntos, retorna em ordem
    cronológica (ASC). Caso contrário, retorna os mais recentes primeiro (DESC).
    Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                base_query = """
                    SELECT id, title, start_time, end_time, location, notes
                    FROM events
                    WHERE 1=1
                """
                params = []

                if date_from_local and date_to_local:
                    base_query += """
                        AND DATE(start_time AT TIME ZONE 'America/Sao_Paulo')
                            BETWEEN %s AND %s
                    """
                    params.extend([date_from_local, date_to_local])

                if title:
                    base_query += " AND (title ILIKE %s OR notes ILIKE %s)"
                    params.extend([f"%{title}%", f"%{title}%"])

                base_query += " ORDER BY start_time ASC" if (date_from_local and date_to_local) else " ORDER BY start_time DESC"

                cur.execute(base_query, params)
                rows = cur.fetchall()

                events = [
                    {
                        "id":         row[0],
                        "title":      row[1],
                        "start_time": str(row[2]),
                        "end_time":   str(row[3]) if row[3] else None,
                        "location":   row[4],
                        "notes":      row[5],
                    }
                    for row in rows
                ]

                logger.info("QUERY OK | query_events total=%s", len(events))

                return Response.ok(total_records=len(events), events=events)

            except Exception as e:
                logger.error("QUERY ERRO | query_events | %s", e)
                return Response.error(e)


@tool("update_event", args_schema=UpdateEventArgs)
@log_tool
def update_event(
    id: Optional[int] = None,
    match_text: Optional[str] = None,
    date_local: Optional[str] = None,
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Atualiza campos de um evento existente.

    Localização por ID direto (id) ou por texto + data (match_text + date_local).
    Quando localizado por texto, atualiza o evento mais recente que combine.
    Pelo menos um campo de atualização deve ser fornecido.
    Retorna o registro atualizado completo após o commit.
    """

    if not any([title, start_time, end_time, location, notes]):
        return Response.error("Nada para atualizar: forneça pelo menos um campo.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                target_id = id
                if target_id is None:
                    if not match_text or not date_local:
                        return Response.error("Sem 'id': informe match_text E date_local para localizar o evento.")

                    cur.execute("""
                        SELECT id FROM events
                        WHERE (title ILIKE %s OR notes ILIKE %s)
                          AND DATE(start_time AT TIME ZONE 'America/Sao_Paulo') = %s
                        ORDER BY start_time DESC
                        LIMIT 1;
                    """, (f"%{match_text}%", f"%{match_text}%", date_local))

                    row = cur.fetchone()
                    if not row:
                        return Response.error("Nenhum evento encontrado para os filtros fornecidos.")
                    target_id = row[0]

                sets: List[str] = []
                params: List[Any] = []

                if title      is not None: sets.append("title = %s");                   params.append(title)
                if start_time is not None: sets.append("start_time = %s::timestamptz"); params.append(start_time)
                if end_time   is not None: sets.append("end_time = %s::timestamptz");   params.append(end_time)
                if location   is not None: sets.append("location = %s");                params.append(location)
                if notes      is not None: sets.append("notes = %s");                   params.append(notes)

                if not sets:
                    return Response.error("Nenhum campo válido para atualizar.")

                params.append(target_id)
                cur.execute(f"UPDATE events SET {', '.join(sets)} WHERE id = %s;", params)
                rows_affected = cur.rowcount
                conn.commit()

                cur.execute("""
                    SELECT id, title, start_time, end_time, location, notes, source_text
                    FROM events
                    WHERE id = %s;
                """, (target_id,))

                row = cur.fetchone()
                updated = {
                    "id":         row[0],
                    "title":      row[1],
                    "start_time": str(row[2]),
                    "end_time":   str(row[3]) if row[3] else None,
                    "location":   row[4],
                    "notes":      row[5],
                    "source_text": row[6],
                } if row else None

                logger.info("UPDATE OK | id=%s rows_affected=%s", target_id, rows_affected)

                return Response.ok(rows_affected=rows_affected, id=target_id, updated=updated)

            except Exception as e:
                conn.rollback()
                logger.error("UPDATE ERRO | id=%s | %s", target_id, e)
                return Response.error(e)


__all__ = [
    "add_event",
    "query_daily_events",
    "query_events",
    "update_event",
]