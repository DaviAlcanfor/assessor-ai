"""
Persistência do perfil financeiro do usuário.

Estruturado (renda, objetivo, tolerância a risco) fica no Mongo, consultável direto por `user_id`.
Preferências em texto livre ficam no Qdrant, indexadas por embedding: busca por palavra não encontra
"nada de cripto" numa frase que só diz "não quero investimento agressivo".

Só a rota HTTP `/v1/perfil` escreve; o agente financeiro só lê (`PerfilTools`). O `user_id` é sempre
explícito — quem o resolve do `session_context()` é o service.
"""

from uuid import NAMESPACE_DNS, uuid5

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.domain.models.perfil import PerfilFinanceiroDocument, PerfilFinanceiroRecord
from app.domain.types import UserID
from app.infra.mongo import MongoConn, MongoRepo
from app.infra.qdrant import VECTOR_SIZE, QdrantConn, qdrant

_QDRANT_COLLECTION = "perfil_preferencias"
_K_NUMBER = 1


def _ponto_id(user_id: UserID) -> str:
    """ID determinístico por usuário — reenviar o formulário substitui o ponto, não duplica."""

    return str(uuid5(NAMESPACE_DNS, user_id))


class PerfilRepository(MongoRepo[PerfilFinanceiroRecord]):
    """Cadastro financeiro (Mongo) + preferências em texto livre indexadas no Qdrant."""

    collection_name = "perfis_financeiros"

    def __init__(self, conn: MongoConn | None = None, qdrant_conn: QdrantConn | None = None) -> None:
        super().__init__(conn)
        self.qdrant_conn = qdrant_conn or qdrant

    # --- escrita -------------------------------------------------------------

    def salvar(self, dados: PerfilFinanceiroDocument) -> PerfilFinanceiroRecord:
        self.collection.update_one(
            {"user_id": dados.user_id},
            {"$set": dados.model_dump(exclude={"user_id"})},
            upsert=True,
        )

        if dados.preferencias:
            self._indexar_preferencias(dados.user_id, dados.preferencias)
        else:
            self._remover_preferencias(dados.user_id)

        return PerfilFinanceiroRecord(
            user_id=dados.user_id,
            renda_mensal=dados.renda_mensal,
            objetivo=dados.objetivo,
            tolerancia_risco=dados.tolerancia_risco,
            preferencias=dados.preferencias,
        )

    def _garantir_collection(self) -> None:
        if not self.qdrant_conn.client.collection_exists(_QDRANT_COLLECTION):
            self.qdrant_conn.client.create_collection(
                collection_name=_QDRANT_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    def _indexar_preferencias(self, user_id: UserID, preferencias: str) -> None:
        self._garantir_collection()

        vetor = self.qdrant_conn.embeddings_documento.embed_query(preferencias)
        self.qdrant_conn.client.upsert(
            collection_name=_QDRANT_COLLECTION,
            points=[
                PointStruct(
                    id=_ponto_id(user_id),
                    vector=vetor,
                    payload={"user_id": user_id, "preferencias": preferencias},
                )
            ],
        )

    def _remover_preferencias(self, user_id: UserID) -> None:
        """Preferências apagadas no formulário não podem sobreviver no índice."""

        if not self.qdrant_conn.client.collection_exists(_QDRANT_COLLECTION):
            return

        self.qdrant_conn.client.delete(
            collection_name=_QDRANT_COLLECTION,
            points_selector=PointIdsList(points=[_ponto_id(user_id)]),
        )

    # --- leitura -------------------------------------------------------------

    def buscar(self, user_id: UserID) -> PerfilFinanceiroRecord | None:
        """Cadastro cru do Mongo, sem busca semântica."""

        return self.collection.find_one({"user_id": user_id})

    def preferencias_relevantes(self, user_id: UserID, pergunta: str) -> list[str]:
        """Preferências do usuário mais parecidas com a pergunta (busca semântica no Qdrant)."""

        if not pergunta or not self.qdrant_conn.client.collection_exists(_QDRANT_COLLECTION):
            return []

        pontos = self.qdrant_conn.client.query_points(
            collection_name=_QDRANT_COLLECTION,
            query=self.qdrant_conn.embeddings.embed_query(pergunta),
            query_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]),
            limit=_K_NUMBER,
        ).points

        return [str(p.payload["preferencias"]) for p in pontos if p.payload is not None]


perfil_repository = PerfilRepository()


__all__ = ["PerfilRepository", "perfil_repository"]
