"""Casos de uso do FAQ do Assessor.AI (busca semântica no PDF indexado). O Qdrant e os embeddings estão em
`repositories/faq_repository.py`."""

import asyncio

from app.repositories.faq_repository import FaqRepository, TrechoFaq, faq_repository


class FaqService:
    def __init__(self, repository: FaqRepository | None = None) -> None:
        self.repository = repository or faq_repository

    async def buscar(self, pergunta: str) -> list[TrechoFaq]:
        return await asyncio.to_thread(self.repository.buscar, pergunta)


faq_service = FaqService()


__all__ = ["FaqService", "faq_service"]
