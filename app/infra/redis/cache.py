"""Caches no Redis: o perfil do usuário (`services/user_service.py`) e a categoria que o JeV escolheu pra um
nome livre (`services/financeiro_service.py`)."""

from typing import cast

from app.domain.types import UserID
from app.infra.redis.connection import redis

PROFILE_TTL_TIME = 3600
CATEGORIA_TTL_TIME = 7 * 24 * 3600  # o mapeamento nome → categoria quase não muda; a chave já muda com as categorias


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


def _chave_categoria(chave: str) -> str:
    return f"financeiro:categoria:{chave}"


def buscar_categoria_cache(chave: str) -> str | None:
    """A categoria (ou `nenhuma`) que o JeV escolheu antes pra essa `chave`; None = nunca perguntado."""

    return cast("str | None", redis.client.get(_chave_categoria(chave)))


def salvar_categoria_cache(chave: str, escolha: str) -> None:
    redis.client.set(_chave_categoria(chave), escolha, ex=CATEGORIA_TTL_TIME)


__all__ = [
    "CATEGORIA_TTL_TIME",
    "PROFILE_TTL_TIME",
    "buscar_categoria_cache",
    "buscar_perfil_cache",
    "invalidar_perfil_cache",
    "salvar_categoria_cache",
    "salvar_perfil_cache",
]
