"""
Persistência do usuário — a única que cruza três bancos.

Mongo guarda o cadastro e o perfil em texto, Postgres guarda a linha de FK que financeiro/agenda
referenciam, e o Redis guarda a API key (só o hash). Ficam no mesmo repositório porque criar um usuário
significa escrever nos dois primeiros com o mesmo `user_id` — quando isso morava em pacotes separados,
quem chamava tinha que lembrar de acertar os dois na ordem certa.
"""

import hashlib
from typing import cast

from sqlalchemy.dialects.postgresql import insert

from app.domain.identifiers import novo_user_id
from app.domain.models.usuario import UserDocument, UserRecord
from app.domain.types import APIKey, APIKeyHash, UserID
from app.infra.logging import Logging
from app.infra.mongo import MongoConn, MongoRepo
from app.infra.postgres import PostgresConn, postgres
from app.infra.postgres.models import User
from app.infra.redis import RedisConn, redis

logger = Logging.get_logger("usuarios")

API_KEY_TTL_TIME = 3600 * 24


def hash_api_key(api_key: APIKey) -> APIKeyHash:
    return APIKeyHash(hashlib.sha256(api_key.encode()).hexdigest())


def chave_api_key(user_id: UserID) -> str:
    return f"auth:user:{user_id}:api-key-hash"


def chave_api_key_lookup(hashed_key: APIKeyHash) -> str:
    return f"auth:api-key:{hashed_key}"


class UsuarioRepository(MongoRepo[UserRecord]):
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

    def inserir(self, nome: str, email: str) -> UserID:
        logger.info(f"Inserindo novo usuário: {email}")

        user_id = novo_user_id()
        self.collection.insert_one(
            cast("UserRecord", UserDocument(user_id=user_id, nome=nome, email=email).model_dump())
        )

        return user_id

    def buscar(self, user_id: UserID) -> UserRecord | None:
        logger.info(f"Buscando usuário para user_id: {user_id}")

        return self.collection.find_one({"user_id": user_id})

    def buscar_por_email(self, email: str) -> UserRecord | None:
        logger.info(f"Buscando usuário para email: {email}")

        return self.collection.find_one({"email": email})

    def buscar_algum(self) -> UserRecord | None:
        logger.info("Buscando algum usuário existente")

        return self.collection.find_one()

    def listar(self, limit: int = 50) -> list[UserRecord]:
        logger.info("Listando usuários")

        return list(
            self.collection.find({}, {"_id": 0, "user_id": 1, "nome": 1, "email": 1}).limit(limit)
        )

    def atualizar_perfil(self, user_id: UserID, perfil: str) -> None:
        logger.info(f"Atualizando perfil para user_id: {user_id}")

        self.collection.update_one({"user_id": user_id}, {"$set": {"profile": perfil}})

    # --- Mongo + Postgres ----------------------------------------------------

    def garantir_usuario(self, user_id: UserID, nome: str, email: str) -> None:
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

    def alocar_api_key(self, user_id: UserID, api_key: APIKey) -> bool:
        """Falha (False) se o usuário já tem uma key ativa — nunca sobrescreve."""

        r = self.cache.client
        hashed = hash_api_key(api_key)

        if not r.set(chave_api_key(user_id), hashed, ex=API_KEY_TTL_TIME, nx=True):
            logger.warning(f"API key already allocated for user {user_id}.")
            return False

        r.set(chave_api_key_lookup(hashed), user_id, ex=API_KEY_TTL_TIME)

        logger.info(f"Allocated API key for user {user_id}.")
        return True

    def user_id_por_api_key(self, api_key: APIKey) -> UserID | None:
        # a conexão usa decode_responses=True, então o retorno é str (stub do redis diz bytes | str)
        user_id = cast(
            "str | None", self.cache.client.get(chave_api_key_lookup(hash_api_key(api_key)))
        )

        if user_id is None:
            logger.warning("API key not found.")

        return UserID(user_id) if user_id is not None else None


usuario_repository = UsuarioRepository()


__all__ = [
    "API_KEY_TTL_TIME",
    "UsuarioRepository",
    "chave_api_key",
    "chave_api_key_lookup",
    "hash_api_key",
    "usuario_repository",
]
