"""
Perfil financeiro do usuário — dado de apoio do especialista financeiro, não um domínio novo (não
tem agente/nó de grafo próprio).

Estruturado (renda, objetivo, tolerância a risco) fica no Mongo, consultável direto por
`user_id`. Preferências em texto livre ficam no Qdrant, indexadas por embedding: busca por
palavra não encontra "nada de cripto" numa frase que só diz "não quero investimento agressivo".

Só a rota HTTP `/v1/perfil` (`salvar`) escreve aqui. O agente financeiro só lê, via `as_tools()`.
"""

from uuid import NAMESPACE_DNS, uuid5

from langchain_core.tools import StructuredTool
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from assessor_ai.graph.tools.perfil.schemas import (
    ConsultarPerfilArgs,
    PerfilFinanceiroDocument,
    PerfilFinanceiroRecord,
)
from assessor_ai.graph.tools.response import Response, ToolResponse
from assessor_ai.identifiers import UserID, usuario_atual
from assessor_ai.infra.mongo import MongoConn, MongoRepo
from assessor_ai.infra.qdrant import VECTOR_SIZE, QdrantConn, qdrant
from assessor_ai.logging import get_logger

logger = get_logger("perfil_financeiro")

_QDRANT_COLLECTION = "perfil_preferencias"
_K_NUMBER = 1


def _ponto_id(user_id: UserID) -> str:
    """ID determinístico por usuário — reenviar o formulário substitui o ponto, não duplica."""

    return str(uuid5(NAMESPACE_DNS, user_id))


class PerfilRepo(MongoRepo[PerfilFinanceiroRecord]):
    """Cadastro financeiro (Mongo) + preferências em texto livre indexadas no Qdrant."""

    collection_name = "perfis_financeiros"

    def __init__(
        self, conn: MongoConn | None = None, qdrant_conn: QdrantConn | None = None
    ) -> None:
        super().__init__(conn)
        self.qdrant_conn = qdrant_conn or qdrant

    @property
    def usuario(self) -> UserID:
        """Dono do turno atual — nunca um argumento de tool escolhido pelo LLM."""

        return usuario_atual()

    # --- escrita: só a rota HTTP chama, nunca o agente ------------------------

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

    # --- leitura estruturada: rota HTTP `GET /v1/perfil` ---------------------

    def buscar(self, user_id: UserID) -> PerfilFinanceiroRecord | None:
        """Cadastro cru do Mongo, sem busca semântica — só pra tela pré-preencher o formulário."""

        return self.collection.find_one({"user_id": user_id})

    # --- leitura: tool do agente financeiro ---------------------------------

    def consultar_perfil_financeiro(self, pergunta: str) -> ToolResponse:
        """
        Consulta o cadastro financeiro do usuário (renda, objetivo, tolerância a risco) e busca,
        por similaridade semântica, as preferências relevantes para a pergunta atual.

        Se o usuário não tiver perfil cadastrado, retorna cadastrado=False — nesse caso, não
        invente renda/objetivo/tolerância: oriente o usuário a preencher a tela de Perfil.
        """

        try:
            registro = self.collection.find_one({"user_id": self.usuario})

            if registro is None:
                return Response.ok(cadastrado=False)

            return Response.ok(
                cadastrado=True,
                renda_mensal=registro["renda_mensal"],
                objetivo=registro["objetivo"],
                tolerancia_risco=registro["tolerancia_risco"],
                preferencias_relevantes=self._buscar_preferencias(pergunta),
            )
        except Exception as e:
            logger.error("PERFIL ERRO | %s", e)
            return Response.error(e)

    def _buscar_preferencias(self, pergunta: str) -> list[str]:
        if not pergunta or not self.qdrant_conn.client.collection_exists(_QDRANT_COLLECTION):
            return []

        pontos = self.qdrant_conn.client.query_points(
            collection_name=_QDRANT_COLLECTION,
            query=self.qdrant_conn.embeddings.embed_query(pergunta),
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=self.usuario))]
            ),
            limit=_K_NUMBER,
        ).points

        return [str(p.payload["preferencias"]) for p in pontos if p.payload is not None]

    def as_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                self.consultar_perfil_financeiro,
                name="consultar_perfil_financeiro",
                args_schema=ConsultarPerfilArgs,
            )
        ]


__all__ = ["PerfilRepo"]
