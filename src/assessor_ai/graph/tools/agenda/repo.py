from datetime import UTC, datetime

from langchain_core.tools import StructuredTool
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from assessor_ai.graph.tools.agenda.models import Event
from assessor_ai.graph.tools.agenda.schemas import (
    AddEventArgs,
    QueryEventArgs,
    UpdateEventArgs,
)
from assessor_ai.graph.tools.response import Response
from assessor_ai.infra.postgres import (
    PostgresRepo,
    local_date_filter,
    local_date_range_filter,
    transacional,
)
from assessor_ai.logging import get_logger


def _serializar(e: Event) -> dict:
    return {
        "id":         e.id,
        "title":      e.title,
        "start_time": str(e.start_time),
        "end_time":   str(e.end_time) if e.end_time else None,
        "location":   e.location,
        "notes":      e.notes,
    }


class AgendaRepo(PostgresRepo):
    """Eventos de agenda do usuário do turno. Cada método público é uma tool do agente de agenda."""

    log = get_logger("pg_agenda")

    @transacional
    def add_event(
        self,
        s: Session,
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

        event = Event(
            title=title,
            start_time=datetime.fromisoformat(start_time),
            end_time=datetime.fromisoformat(end_time) if end_time else None,
            location=location,
            notes=notes,
            source_text=source_text,
            recorded_at=datetime.now(UTC),
            user_id=self.usuario,
        )
        s.add(event)
        s.flush()

        return Response.ok(id=event.id, recorded_at=str(event.recorded_at))

    @transacional
    def query_daily_events(self, s: Session, date_local: str) -> dict:
        """
        Retorna todos os eventos de um dia específico.

        date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
        """

        stmt = (
            select(Event)
            .where(
                local_date_filter(Event.start_time, date_local),
                Event.user_id == self.usuario,
            )
            .order_by(Event.start_time.asc())
        )
        eventos = [_serializar(e) for e in s.scalars(stmt).all()]

        return Response.ok(date=date_local, total_records=len(eventos), events=eventos)

    @transacional
    def query_events(
        self,
        s: Session,
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

        stmt = select(Event).where(Event.user_id == self.usuario)

        if date_from_local and date_to_local:
            stmt = stmt.where(
                local_date_range_filter(Event.start_time, date_from_local, date_to_local)
            ).order_by(Event.start_time.asc())
        else:
            stmt = stmt.order_by(Event.start_time.desc())

        if title:
            like = f"%{title}%"
            stmt = stmt.where(or_(Event.title.ilike(like), Event.notes.ilike(like)))

        eventos = [_serializar(e) for e in s.scalars(stmt).all()]

        return Response.ok(total_records=len(eventos), events=eventos)

    @transacional
    def update_event(
        self,
        s: Session,
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

        if target_id is None:
            if not match_text or not date_local:
                return Response.error(
                    "Sem 'id': informe match_text E date_local para localizar o evento."
                )

            like = f"%{match_text}%"
            target_id = s.scalar(
                select(Event.id)
                .where(
                    or_(Event.title.ilike(like), Event.notes.ilike(like)),
                    local_date_filter(Event.start_time, date_local),
                    Event.user_id == self.usuario,
                )
                .order_by(Event.start_time.desc())
                .limit(1)
            )
            if not target_id:
                return Response.error("Nenhum evento encontrado para os filtros fornecidos.")

        event = s.get(Event, target_id)
        if event is None or event.user_id != self.usuario:
            return Response.ok(rows_affected=0, id=target_id, updated=None)

        if title      is not None: event.title = title
        if start_time is not None: event.start_time = datetime.fromisoformat(start_time)
        if end_time   is not None: event.end_time = datetime.fromisoformat(end_time)
        if location   is not None: event.location = location
        if notes      is not None: event.notes = notes

        s.flush()

        updated = _serializar(event) | {"source_text": event.source_text}

        return Response.ok(rows_affected=1, id=target_id, updated=updated)

    def as_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(self.add_event, name="add_event", args_schema=AddEventArgs),
            StructuredTool.from_function(self.query_daily_events, name="query_daily_events"),
            StructuredTool.from_function(
                self.query_events, name="query_events", args_schema=QueryEventArgs
            ),
            StructuredTool.from_function(
                self.update_event, name="update_event", args_schema=UpdateEventArgs
            ),
        ]


__all__ = ["AgendaRepo"]
