from typing import ClassVar

from app.graph.tools.agenda.schemas import AddEventArgs, QueryEventArgs, UpdateEventArgs
from app.graph.tools.base import Schemas, ToolSet
from app.graph.tools.response import Response, ToolResponse
from app.services.agenda_service import AgendaService, agenda_service


class AgendaTools(ToolSet):
    """Eventos de agenda do usuário do turno. Cada método público é uma tool do agente de agenda; a regra
    e o acesso ao banco estão em `AgendaService`."""

    schemas: ClassVar[Schemas] = {
        "add_event": AddEventArgs,
        "query_events": QueryEventArgs,
        "update_event": UpdateEventArgs,
    }

    def __init__(self, service: AgendaService | None = None) -> None:
        self.service = service or agenda_service

    async def add_event(
        self,
        title: str,
        start_time: str,
        source_text: str,
        notes: str,
        end_time: str | None = None,
        location: str | None = None,
    ) -> ToolResponse:
        """
        Insere um evento na agenda do usuário.

        start_time e end_time devem estar no formato ISO 8601.
        recorded_at é preenchido automaticamente com NOW().
        """

        criado = await self.service.adicionar(title, start_time, source_text, notes, end_time, location)

        return Response.ok(**criado)

    async def query_daily_events(self, date_local: str) -> ToolResponse:
        """
        Retorna todos os eventos de um dia específico.

        date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
        """

        eventos = await self.service.do_dia(date_local)

        return Response.ok(date=date_local, total_records=len(eventos), events=eventos)

    async def query_events(
        self,
        date_from_local: str | None = None,
        date_to_local: str | None = None,
        title: str | None = None,
    ) -> ToolResponse:
        """
        Consulta eventos com filtros opcionais por período e título.

        Quando date_from_local e date_to_local são informados juntos, retorna em ordem
        cronológica (ASC). Caso contrário, retorna os mais recentes primeiro (DESC).
        Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
        """

        eventos = await self.service.consultar(date_from_local, date_to_local, title)

        return Response.ok(total_records=len(eventos), events=eventos)

    async def update_event(
        self,
        id: int | None = None,
        match_text: str | None = None,
        date_local: str | None = None,
        title: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> ToolResponse:
        """
        Atualiza campos de um evento existente.

        Localização por ID direto (id) ou por texto + data (match_text + date_local).
        Quando localizado por texto, atualiza o evento mais recente que combine.
        Pelo menos um campo de atualização deve ser fornecido.
        Retorna o registro atualizado completo após o commit.
        """

        atualizado = await self.service.atualizar(
            id, match_text, date_local, title, start_time, end_time, location, notes
        )

        if atualizado is None:
            return Response.ok(rows_affected=0, id=id, updated=None)

        return Response.ok(rows_affected=1, id=atualizado["id"], updated=atualizado)


__all__ = ["AgendaTools"]
