"""Casos de uso do perfil financeiro: a rota `/v1/perfil` grava e lê; o agente financeiro só consulta
(`PerfilTools`). Mongo (cadastro) e Qdrant (preferências em texto livre) ficam em
`repositories/perfil_repository.py`."""

import asyncio

from app.domain.models.perfil import (
    PerfilFinanceiroDocument,
    PerfilFinanceiroRecord,
    ToleranciaRisco,
)
from app.domain.types import UserID
from app.infra.context import current_user
from app.repositories.perfil_repository import PerfilRepository, perfil_repository


class PerfilService:
    def __init__(self, repository: PerfilRepository | None = None) -> None:
        self.repository = repository or perfil_repository

    async def salvar(
        self,
        user_id: UserID,
        renda_mensal: float,
        objetivo: str,
        tolerancia_risco: ToleranciaRisco,
        preferencias: str | None,
    ) -> PerfilFinanceiroRecord:
        """Escreve no Mongo (estruturado) e no Qdrant (preferências) a partir do mesmo ponto."""

        dados = PerfilFinanceiroDocument(
            user_id=user_id,
            renda_mensal=renda_mensal,
            objetivo=objetivo,
            tolerancia_risco=tolerancia_risco,
            preferencias=preferencias,
        )

        return await asyncio.to_thread(self.repository.salvar, dados)

    async def obter(self, user_id: UserID) -> PerfilFinanceiroRecord | None:
        return await asyncio.to_thread(self.repository.buscar, user_id)

    async def consultar_para_agente(self, pergunta: str) -> dict[str, object]:
        """O perfil do usuário do turno + as preferências mais parecidas com a pergunta. Sem cadastro
        devolve `cadastrado=False` — o agente não deve inventar renda/objetivo/tolerância."""

        user_id = current_user()
        registro = await asyncio.to_thread(self.repository.buscar, user_id)

        if registro is None:
            return {"cadastrado": False}

        preferencias = await asyncio.to_thread(self.repository.preferencias_relevantes, user_id, pergunta)

        return {
            "cadastrado": True,
            "renda_mensal": registro["renda_mensal"],
            "objetivo": registro["objetivo"],
            "tolerancia_risco": registro["tolerancia_risco"],
            "preferencias_relevantes": preferencias,
        }


perfil_service = PerfilService()


__all__ = ["PerfilService", "perfil_service"]
