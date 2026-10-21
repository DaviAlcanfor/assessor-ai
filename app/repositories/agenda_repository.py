"""Persistência dos eventos de agenda (Postgres), sem regra de negócio.

Mesmo desenho de `financeiro_repository.py`: `user_id` explícito, toda query filtra por ele, e localizar
+ gravar acontecem na mesma transação.
"""

from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.errors import RegistroNaoEncontrado
from app.infra.postgres import (
    PostgresRepo,
    local_date_filter,
    local_date_range_filter,
    transacional,
)
from app.infra.postgres.models import Event


class NovoEvento(TypedDict):
    title:       str
    start_time:  datetime
    end_time:    datetime | None
    location:    str | None
    notes:       str
    source_text: str
    recorded_at: datetime


class EventoCriado(TypedDict):
    id:          int
    recorded_at: str


class EventRecord(TypedDict):
    id:         int
    title:      str
    start_time: str
    end_time:   str | None
    location:   str | None
    notes:      str | None


class EventoAtualizado(EventRecord):
    source_text: str


class CamposEvento(TypedDict):
    """Só o que o usuário pediu pra mudar; ausente = não mexe."""

    title:      NotRequired[str]
    start_time: NotRequired[datetime]
    end_time:   NotRequired[datetime]
    location:   NotRequired[str]
    notes:      NotRequired[str]


def _serializar(e: Event) -> EventRecord:
    return {
        "id":         e.id,
        "title":      e.title,
        "start_time": str(e.start_time),
        "end_time":   str(e.end_time) if e.end_time else None,
        "location":   e.location,
        "notes":      e.notes,
    }


def _id_por_texto(s: Session, user_id: UUID, match_text: str, date_local: str) -> int | None:
    like = f"%{match_text}%"
    return s.scalar(
        select(Event.id)
        .where(
            or_(Event.title.ilike(like), Event.notes.ilike(like)),
            local_date_filter(Event.start_time, date_local),
            Event.user_id == user_id,
        )
        .order_by(Event.start_time.desc())
        .limit(1)
    )


class AgendaRepository(PostgresRepo):
    @transacional
    def adicionar(self, s: Session, user_id: UUID, dados: NovoEvento) -> EventoCriado:
        event = Event(**dados, user_id=user_id)
        s.add(event)
        s.flush()

        return {"id": event.id, "recorded_at": str(event.recorded_at)}

    @transacional
    def do_dia(self, s: Session, user_id: UUID, date_local: str) -> list[EventRecord]:
        stmt = (
            select(Event)
            .where(local_date_filter(Event.start_time, date_local), Event.user_id == user_id)
            .order_by(Event.start_time.asc())
        )

        return [_serializar(e) for e in s.scalars(stmt).all()]

    @transacional
    def consultar(
        self,
        s: Session,
        user_id: UUID,
        date_from_local: str | None,
        date_to_local: str | None,
        title: str | None,
    ) -> list[EventRecord]:
        """Com período completo (de/até) vem em ordem cronológica; senão, os mais recentes primeiro."""

        stmt = select(Event).where(Event.user_id == user_id)

        if date_from_local and date_to_local:
            stmt = stmt.where(
                local_date_range_filter(Event.start_time, date_from_local, date_to_local)
            ).order_by(Event.start_time.asc())
        else:
            stmt = stmt.order_by(Event.start_time.desc())

        if title:
            like = f"%{title}%"
            stmt = stmt.where(or_(Event.title.ilike(like), Event.notes.ilike(like)))

        return [_serializar(e) for e in s.scalars(stmt).all()]

    @transacional
    def atualizar(
        self,
        s: Session,
        user_id: UUID,
        evento_id: int | None,
        match_text: str | None,
        date_local: str | None,
        campos: CamposEvento,
    ) -> EventoAtualizado | None:
        """Localiza por `evento_id` ou, sem ele, por texto + dia (o mais recente que combine) e atualiza.
        `None` = o id não existe ou é de outro usuário; sem combinação por texto, levanta
        `RegistroNaoEncontrado`."""

        alvo = evento_id

        if alvo is None:
            assert match_text and date_local  # o service já validou
            alvo = _id_por_texto(s, user_id, match_text, date_local)
            if not alvo:
                raise RegistroNaoEncontrado("Nenhum evento encontrado para os filtros fornecidos.")

        event = s.get(Event, alvo)
        if event is None or event.user_id != user_id:
            return None

        if "title" in campos:      event.title = campos["title"]
        if "start_time" in campos: event.start_time = campos["start_time"]
        if "end_time" in campos:   event.end_time = campos["end_time"]
        if "location" in campos:   event.location = campos["location"]
        if "notes" in campos:      event.notes = campos["notes"]

        s.flush()

        return EventoAtualizado(**_serializar(event), source_text=event.source_text)


agenda_repository = AgendaRepository()


__all__ = [
    "AgendaRepository",
    "CamposEvento",
    "EventRecord",
    "EventoAtualizado",
    "EventoCriado",
    "NovoEvento",
    "agenda_repository",
]
