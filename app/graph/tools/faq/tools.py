from typing import ClassVar

from app.graph.tools.base import Schemas, ToolSet
from app.graph.tools.faq.schemas import FaqRetrieverArgs
from app.graph.tools.response import Response, ToolResponse
from app.services.faq_service import FaqService, faq_service


class FaqTools(ToolSet):
    """FAQ do Assessor.AI (PDF indexado no Qdrant). A busca está em `FaqService`."""

    schemas: ClassVar[Schemas] = {"faq_retriever": FaqRetrieverArgs}

    def __init__(self, service: FaqService | None = None) -> None:
        self.service = service or faq_service

    async def faq_retriever(self, question: str) -> ToolResponse:
        """
        Consulta o PDF de FAQ com as perguntas de funcionamento do Assessor AI.
        """

        return Response.ok(results=await self.service.buscar(question))


__all__ = ["FaqTools"]
