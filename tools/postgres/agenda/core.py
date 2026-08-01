from datetime import UTC, datetime

from langchain.tools import tool
from sqlalchemy import or_, select

from config.decorators import log_tool
from config.logging import get_logger
from tools.postgres.agenda.schemas import (
    AddEventArgs,
    QueryEventArgs,
    UpdateEventArgs,
)
from tools.postgres.connection import get_session
from tools.postgres.helpers import local_date_filter, local_date_range_filter
from tools.postgres.models import Event
from tools.response import Response

logger = get_logger("pg_events")


@tool("add_event", args_schema=AddEventArgs)
@log_tool
def add_event(
    title: str,
    start_time: str,
    source_text: str,
    notes: str,
    end_time: str | None = None,
    location: str | None = None,
) -> dict:
    """
    Insere um evento na agenda do usuário.

    start_time e end_time devem estar no formato ISO 8601.
    recorded_at é preenchido automaticamente com NOW().
    """

    with get_session() as session:
        try:
            event = Event(
                title=title,
                start_time=datetime.fromisoformat(start_time),
                end_time=datetime.fromisoformat(end_time) if end_time else None,
                location=location,
                notes=notes,
                source_text=source_text,
                recorded_at=datetime.now(UTC),
            )
            session.add(event)
            session.flush()

            logger.info("INSERT OK | id=%s title=%s start_time=%s", event.id, title, start_time)

            return Response.ok(id=event.id, recorded_at=str(event.recorded_at))

        except Exception as e:
            logger.error("INSERT ERRO | %s", e)
            return Response.error(e)


@tool("query_daily_events")
@log_tool
def query_daily_events(date_local: str) -> dict:
    """
    Retorna todos os eventos de um dia específico.

    date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
    """

    with get_session() as session:
        try:
            stmt = (
                select(Event)
                .where(local_date_filter(Event.start_time, date_local))
                .order_by(Event.start_time.asc())
            )
            rows = session.scalars(stmt).all()

            events = [
                {
                    "id":         e.id,
                    "title":      e.title,
                    "start_time": str(e.start_time),
                    "end_time":   str(e.end_time) if e.end_time else None,
                    "location":   e.location,
                    "notes":      e.notes,
                }
                for e in rows
            ]

            logger.info("QUERY OK | query_daily_events date=%s total=%s", date_local, len(events))

            return Response.ok(date=date_local, total_records=len(events), events=events)

        except Exception as e:
            logger.error("QUERY ERRO | query_daily_events | %s", e)
            return Response.error(e)


@tool("query_events", args_schema=QueryEventArgs)
@log_tool
def query_events(
    date_from_local: str | None = None,
    date_to_local: str | None = None,
    title: str | None = None,
) -> dict:
    """
    Consulta eventos com filtros opcionais por período e título.

    Quando date_from_local e date_to_local são informados juntos, retorna em ordem
    cronológica (ASC). Caso contrário, retorna os mais recentes primeiro (DESC).
    Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
    """

    with get_session() as session:
        try:
            stmt = select(Event)

            if date_from_local and date_to_local:
                stmt = stmt.where(local_date_range_filter(Event.start_time, date_from_local, date_to_local))
                stmt = stmt.order_by(Event.start_time.asc())
            else:
                stmt = stmt.order_by(Event.start_time.desc())

            if title:
                like = f"%{title}%"
                stmt = stmt.where(or_(Event.title.ilike(like), Event.notes.ilike(like)))

            rows = session.scalars(stmt).all()

            events = [
                {
                    "id":         e.id,
                    "title":      e.title,
                    "start_time": str(e.start_time),
                    "end_time":   str(e.end_time) if e.end_time else None,
                    "location":   e.location,
                    "notes":      e.notes,
                }
                for e in rows
            ]

            logger.info("QUERY OK | query_events total=%s", len(events))

            return Response.ok(total_records=len(events), events=events)

        except Exception as e:
            logger.error("QUERY ERRO | query_events | %s", e)
            return Response.error(e)


@tool("update_event", args_schema=UpdateEventArgs)
@log_tool
def update_event(
    id: int | None = None,
    match_text: str | None = None,
    date_local: str | None = None,
    title: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    location: str | None = None,
    notes: str | None = None,
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

    target_id = id

    with get_session() as session:
        try:
            if target_id is None:
                if not match_text or not date_local:
                    return Response.error("Sem 'id': informe match_text E date_local para localizar o evento.")

                like = f"%{match_text}%"
                target_id = session.scalar(
                    select(Event.id)
                    .where(
                        or_(Event.title.ilike(like), Event.notes.ilike(like)),
                        local_date_filter(Event.start_time, date_local),
                    )
                    .order_by(Event.start_time.desc())
                    .limit(1)
                )
                if not target_id:
                    return Response.error("Nenhum evento encontrado para os filtros fornecidos.")

            event = session.get(Event, target_id)
            if event is None:
                return Response.ok(rows_affected=0, id=target_id, updated=None)

            if title      is not None: event.title = title
            if start_time is not None: event.start_time = datetime.fromisoformat(start_time)
            if end_time   is not None: event.end_time = datetime.fromisoformat(end_time)
            if location   is not None: event.location = location
            if notes      is not None: event.notes = notes

            session.flush()

            updated = {
                "id":         event.id,
                "title":      event.title,
                "start_time": str(event.start_time),
                "end_time":   str(event.end_time) if event.end_time else None,
                "location":   event.location,
                "notes":      event.notes,
                "source_text": event.source_text,
            }

            logger.info("UPDATE OK | id=%s rows_affected=1", target_id)

            return Response.ok(rows_affected=1, id=target_id, updated=updated)

        except Exception as e:
            logger.error("UPDATE ERRO | id=%s | %s", target_id, e)
            return Response.error(e)


__all__ = [
    "add_event",
    "query_daily_events",
    "query_events",
    "update_event",
]
