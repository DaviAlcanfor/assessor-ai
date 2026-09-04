"""Cache do perfil do usuário no Redis. Consumido por `repositories/chat_repository.py`."""

from typing import cast

from assessor_ai.identifiers import UserID
from assessor_ai.infra.redis import redis

PROFILE_TTL_TIME = 3600


def _chave_perfil(user_id: UserID) -> str:
    return f"user:{user_id}:profile"


def buscar_perfil_cache(user_id: UserID) -> str | None:
    r = redis.client

    # connection usa decode_responses=True, então o retorno é str (stub do redis diz bytes | str)
    return cast("str | None", r.get(_chave_perfil(user_id)))


def salvar_perfil_cache(user_id: UserID, perfil: str) -> None:
    redis.client.set(_chave_perfil(user_id), perfil, ex=PROFILE_TTL_TIME)


def invalidar_perfil_cache(user_id: UserID) -> None:
    redis.client.delete(_chave_perfil(user_id))


__all__ = [
    "PROFILE_TTL_TIME",
    "buscar_perfil_cache",
    "invalidar_perfil_cache",
    "salvar_perfil_cache",
]
