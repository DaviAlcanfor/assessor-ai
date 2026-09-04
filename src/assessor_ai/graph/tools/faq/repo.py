from langchain_core.tools import StructuredTool

from assessor_ai.config import settings
from assessor_ai.graph.tools.faq.schemas import FaqRetrieverArgs, SearchResponse
from assessor_ai.graph.tools.response import Response
from assessor_ai.infra.qdrant import QdrantConn, qdrant
from assessor_ai.logging import get_logger

logger = get_logger("qdrant_faq")

_K_NUMBER = 5


class FaqRepo:
    """
    Busca semântica no PDF de FAQ indexado no Qdrant.

    Client e modelo de embedding vêm da conexão (`infra/qdrant.py`) — antes o
    `GoogleGenerativeAIEmbeddings` era reconstruído a cada pergunta.
    """

    def __init__(self, conn: QdrantConn | None = None) -> None:
        self.conn = conn or qdrant

    def faq_retriever(self, question: str) -> dict:
        """
        Consulta o PDF de FAQ com as perguntas de funcionamento do Assessor AI.
        """

        try:
            colecao = settings.QDRANT_COLLECTION_NAME

            if not self.conn.client.collection_exists(colecao):
                logger.error(
                    "FAQ ERRO | collection '%s' não existe — rode: python -m assessor_ai.graph.tools.faq.ingest",
                    colecao,
                )
                return Response.error("Base de FAQ ainda não foi indexada.")

            pontos = self.conn.client.query_points(
                collection_name=colecao,
                query=self.conn.embeddings.embed_query(question),
                limit=_K_NUMBER,
            ).points

            resultados = [
                SearchResponse(
                    text=payload["text"],
                    file=payload["file"],
                    page=payload["page"],
                    score=p.score,
                )
                for p in pontos
                if (payload := p.payload) is not None
            ]

            return Response.ok(results=[r.model_dump() for r in resultados])

        except Exception as e:
            logger.error("FAQ ERRO | %s", e)
            return Response.error(e)

    def as_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                self.faq_retriever, name="faq_retriever", args_schema=FaqRetrieverArgs
            )
        ]


__all__ = ["FaqRepo"]
