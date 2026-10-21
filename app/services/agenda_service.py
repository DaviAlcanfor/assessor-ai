"""Casos de uso da agenda do usuário do turno (tools do agente e MCP). Regra e escopo aqui; SQL em
`repositories/agenda_repository.py`."""

import asyncio
from datetime import UTC, datetime

from app.domain.errors import DadosInvalidos
from app.infra.context import current_user_id
from app.repositories.agenda_repository import (
    AgendaRepository,
    CamposEvento,
    EventoAtualizado,
    EventoCriado,
    EventRecord,
    NovoEvento,
    agenda_repository,
)


def _data_hora(texto: str) -> datetime:
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        raise DadosInvalidos(f"Data/hora inválida: '{texto}'. Use ISO 8601 (ex.: 2026-10-21T15:30:00-03:00).") from None


class AgendaService:
    def __init__(self, repository: AgendaRepository | None = None) -> None:
        self.repository = repository or agenda_repository

    async def adicionar(
        self,
        title: str,
        start_time: str,
        source_text: str,
        notes: str,
        end_time: str | None = None,
        location: str | None = None,
    ) -> EventoCriado:
        dados = NovoEvento(
            title=title,
            start_time=_data_hora(start_time),
            end_time=_data_hora(end_time) if end_time else None,
            location=location,
            notes=notes,
            source_text=source_text,
            recorded_at=datetime.now(UTC),
        )

        return await asyncio.to_thread(self.repository.adicionar, current_user_id(), dados)

    async def do_dia(self, date_local: str) -> list[EventRecord]:
        return await asyncio.to_thread(self.repository.do_dia, current_user_id(), date_local)

    async def consultar(
        self,
        date_from_local: str | None = None,
        date_to_local: str | None = None,
        title: str | None = None,
    ) -> list[EventRecord]:
        return await asyncio.to_thread(
            self.repository.consultar, current_user_id(), date_from_local, date_to_local, title
        )

    async def atualizar(
        self,
        id: int | None = None,
        match_text: str | None = None,
        date_local: str | None = None,
        title: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> EventoAtualizado | None:
        """`None` = o id informado não existe (ou é de outro usuário)."""

        campos = CamposEvento()
        if title is not None:      campos["title"] = title
        if start_time is not None: campos["start_time"] = _data_hora(start_time)
        if end_time is not None:   campos["end_time"] = _data_hora(end_time)
        if location is not None:   campos["location"] = location
        if notes is not None:      campos["notes"] = notes

        if not campos:
            raise DadosInvalidos("Nada para atualizar: forneça pelo menos um campo.")

        if id is None and not (match_text and date_local):
            raise DadosInvalidos("Sem 'id': informe match_text E date_local para localizar o evento.")

        return await asyncio.to_thread(
            self.repository.atualizar, current_user_id(), id, match_text, date_local, campos
        )


agenda_service = AgendaService()


__all__ = ["AgendaService", "agenda_service"]
