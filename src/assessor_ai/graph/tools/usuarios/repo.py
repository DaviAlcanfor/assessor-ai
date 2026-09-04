"""
Usuário — a única feature que cruza os três bancos.

Mongo guarda o cadastro e o perfil, Postgres guarda a linha de FK que financeiro/agenda
referenciam, e o Redis guarda a API key. Ficam no mesmo repositório porque criar um usuário
significa escrever nos dois primeiros com o mesmo `user_id` — quando isso morava em três
pacotes separados, quem chamava tinha que lembrar de acertar os dois na ordem certa.
"""

from typing import cast
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert

from assessor_ai.graph.tools.usuarios.models import User
from assessor_ai.graph.tools.usuarios.schemas import (
    API_KEY_TTL_TIME,
    UserDocument,
    chave_api_key,
    chave_api_key_lookup,
    hash_api_key,
)
from assessor_ai.infra.mongo import MongoConn, MongoRepo
from assessor_ai.infra.postgres import PostgresConn, postgres
from assessor_ai.infra.redis import RedisConn, redis
from assessor_ai.logging import get_logger

logger = get_logger("usuarios")


class UsuariosRepo(MongoRepo):
    """Cadastro e perfil (Mongo) + linha espelho no Postgres + API key no Redis."""

    collection_name = "users"

    def __init__(
        self,
        conn: MongoConn | None = None,
        pg: PostgresConn | None = None,
        cache: RedisConn | None = None,
    ) -> None:
        super().__init__(conn)
        self.pg = pg or postgres
        self.cache = cache or redis

    # --- Mongo ---------------------------------------------------------------

    def inserir(self, nome: str, email: str) -> str:
        logger.info(f"Inserindo novo usuário: {email}")

        user_id = str(uuid4())
        self.collection.insert_one(
            UserDocument(user_id=user_id, nome=nome, email=email).model_dump()
        )

        return user_id

    def buscar(self, user_id: str) -> dict | None:
        logger.info(f"Buscando usuário para user_id: {user_id}")

        return self.collection.find_one({"user_id": user_id})

    def buscar_por_email(self, email: str) -> dict | None:
        logger.info(f"Buscando usuário para email: {email}")

        return self.collection.find_one({"email": email})

    def buscar_algum(self) -> dict | None:
        logger.info("Buscando algum usuário existente")

        return self.collection.find_one()

    def listar(self, limit: int = 50) -> list[dict]:
        logger.info("Listando usuários")

        return list(
            self.collection.find({}, {"_id": 0, "user_id": 1, "nome": 1, "email": 1}).limit(limit)
        )

    def atualizar_perfil(self, user_id: str, perfil: str) -> None:
        logger.info(f"Atualizando perfil para user_id: {user_id}")

        self.collection.update_one({"user_id": user_id}, {"$set": {"profile": perfil}})

    # --- Mongo + Postgres ----------------------------------------------------

    def garantir_usuario(self, user_id: str, nome: str, email: str) -> None:
        """
        Cria o usuário nos dois bancos com o mesmo `user_id`, se ainda não existir.
        Idempotente dos dois lados (`$setOnInsert` / `ON CONFLICT DO NOTHING`).
        """

        self.collection.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "nome":    nome,
                "email":   email,
                "profile": "",
            }},
            upsert=True,
        )

        with self.pg.session() as s:
            s.execute(insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=["id"]))

    # --- Redis ---------------------------------------------------------------

    def alocar_api_key(self, user_id: str, api_key: str) -> bool:
        """Falha (False) se o usuário já tem uma key ativa — nunca sobrescreve."""

        r = self.cache.client
        hashed = hash_api_key(api_key)

        if not r.set(chave_api_key(user_id), hashed, ex=API_KEY_TTL_TIME, nx=True):
            logger.warning(f"API key already allocated for user {user_id}.")
            return False

        r.set(chave_api_key_lookup(hashed), user_id, ex=API_KEY_TTL_TIME)

        logger.info(f"Allocated API key for user {user_id}.")
        return True

    def user_id_por_api_key(self, api_key: str) -> str | None:
        # a conexão usa decode_responses=True, então o retorno é str (stub do redis diz bytes | str)
        user_id = cast(
            "str | None", self.cache.client.get(chave_api_key_lookup(hash_api_key(api_key)))
        )

        if user_id is None:
            logger.warning("API key not found.")

        return user_id


__all__ = ["UsuariosRepo"]
