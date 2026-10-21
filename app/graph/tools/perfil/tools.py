from typing import ClassVar

from app.graph.tools.base import Schemas, ToolSet
from app.graph.tools.perfil.schemas import ConsultarPerfilArgs
from app.graph.tools.response import Response, ToolResponse
from app.services.perfil_service import PerfilService, perfil_service


class PerfilTools(ToolSet):
    """Perfil financeiro do usuário do turno, só leitura: dado de apoio do agente financeiro (quem grava é a
    rota HTTP `/v1/perfil`). A regra e o armazenamento estão em `PerfilService`."""

    schemas: ClassVar[Schemas] = {"consultar_perfil_financeiro": ConsultarPerfilArgs}

    def __init__(self, service: PerfilService | None = None) -> None:
        self.service = service or perfil_service

    async def consultar_perfil_financeiro(self, pergunta: str) -> ToolResponse:
        """
        Consulta o cadastro financeiro do usuário (renda, objetivo, tolerância a risco) e busca,
        por similaridade semântica, as preferências relevantes para a pergunta atual.

        Se o usuário não tiver perfil cadastrado, retorna cadastrado=False — nesse caso, não
        invente renda/objetivo/tolerância: oriente o usuário a preencher a tela de Perfil.
        """

        return Response.ok(**await self.service.consultar_para_agente(pergunta))


__all__ = ["PerfilTools"]
