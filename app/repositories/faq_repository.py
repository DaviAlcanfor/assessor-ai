"""Busca semântica no PDF de FAQ indexado no Qdrant (`python -m app.graph.tools.faq.ingest` indexa).

Client e modelo de embedding vêm da conexão (`infra/qdrant`) — antes o `GoogleGenerativeAIEmbeddings`
era reconstruído a cada pergunta.
"""

from typing import TypedDict

from app.domain.errors import RegistroNaoEncontrado
from app.infra.logging import Logging
from app.infra.qdrant import QdrantConn, qdrant
from app.settings import settings

logger = Logging.get_logger("qdrant_faq")

_K_NUMBER = 5


class TrechoFaq(TypedDict):
    text:  str
    file:  str
    page:  int
    score: float


class FaqRepository:
    def __init__(self, conn: QdrantConn | None = None) -> None:
        self.conn = conn or qdrant

    def buscar(self, pergunta: str) -> list[TrechoFaq]:
        colecao = settings.database.qdrant_collection_name

        if not self.conn.client.collection_exists(colecao):
            logger.error(
                "FAQ ERRO | collection '%s' não existe — rode: python -m app.graph.tools.faq.ingest", colecao
            )
            raise RegistroNaoEncontrado("Base de FAQ ainda não foi indexada.")

        pontos = self.conn.client.query_points(
            collection_name=colecao,
            query=self.conn.embeddings.embed_query(pergunta),
            limit=_K_NUMBER,
        ).points

        return [
            TrechoFaq(
                text=payload["text"], file=payload["file"], page=payload["page"], score=p.score
            )
            for p in pontos
            if (payload := p.payload) is not None
        ]


faq_repository = FaqRepository()


__all__ = ["FaqRepository", "TrechoFaq", "faq_repository"]
