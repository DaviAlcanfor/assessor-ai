"""Casos de uso do usuário: cadastro, perfil em texto (com cache) e API key. Rotas, TUI, A2A e MCP chegam
aqui; o armazenamento está em `repositories/usuario_repository.py` (síncrono, chamado com `to_thread`)."""

import asyncio

from faker import Faker
from langsmith import traceable

from app.domain.identifiers import novo_user_id
from app.domain.models.usuario import UserRecord
from app.domain.privacy import anonimizar_entrada
from app.domain.types import APIKey, UserID
from app.infra.redis.cache import (
    buscar_perfil_cache,
    salvar_perfil_cache,
)
from app.repositories.usuario_repository import usuario_repository

_fake = Faker()


def _gerar_usuario_mock() -> dict[str, str]:
    return {"name": _fake.name(), "email": _fake.email()}


def _redigir_saida_perfil(perfil: str | None) -> dict[str, str]:
    texto, _ = anonimizar_entrada(perfil or "")
    return {"perfil": texto}


async def garantir_usuario(user_id: UserID, nome: str, email: str) -> None:
    await asyncio.to_thread(usuario_repository.garantir_usuario, user_id, nome=nome, email=email)


async def buscar_usuario_existente() -> UserRecord | None:
    return await asyncio.to_thread(usuario_repository.buscar_algum)


async def listar_usuarios() -> list[UserRecord]:
    return await asyncio.to_thread(usuario_repository.listar)


async def obter_ou_criar_usuario(nome: str, email: str) -> UserID:
    usuario = await asyncio.to_thread(usuario_repository.buscar_por_email, email)

    if usuario:
        return usuario["user_id"]

    user_id = novo_user_id()
    await garantir_usuario(user_id, nome=nome, email=email)

    return user_id


async def obter_usuario_padrao() -> UserID:
    """
    Reaproveita o primeiro usuário existente, ou cria um mock — mesmo bootstrap usado por
    TUI (`chat_service.iniciar_sessao`) e pela auth da API quando `API__KEY_AUTH_ENABLED=false`.
    """

    usuario_existente = await buscar_usuario_existente()

    if usuario_existente:
        return usuario_existente["user_id"]

    user_id = novo_user_id()
    novo_usuario = _gerar_usuario_mock()
    await garantir_usuario(user_id, nome=novo_usuario["name"], email=novo_usuario["email"])

    return user_id


@traceable(run_type="tool", name="buscar_perfil", process_outputs=_redigir_saida_perfil)
async def buscar_perfil(user_id: UserID) -> str:
    """
    Perfil em texto do usuário: no cache Redis; se não estiver lá, no MongoDB (e salva no cache).
    """

    perfil_cache = await asyncio.to_thread(buscar_perfil_cache, user_id)

    if perfil_cache is not None:
        return perfil_cache

    usuario = await asyncio.to_thread(usuario_repository.buscar, user_id)
    perfil = usuario.get("profile", "") if usuario else ""

    await asyncio.to_thread(salvar_perfil_cache, user_id, perfil)
    return perfil


async def alocar_api_key(user_id: UserID, api_key: APIKey) -> bool:
    """`False` se o usuário já tem uma key ativa: nunca sobrescreve."""

    return await asyncio.to_thread(usuario_repository.alocar_api_key, user_id, api_key)


async def buscar_user_id_por_api_key(api_key: APIKey) -> UserID | None:
    return await asyncio.to_thread(usuario_repository.user_id_por_api_key, api_key)


__all__ = [
    "alocar_api_key",
    "buscar_perfil",
    "buscar_user_id_por_api_key",
    "buscar_usuario_existente",
    "garantir_usuario",
    "listar_usuarios",
    "obter_ou_criar_usuario",
    "obter_usuario_padrao",
]
