"""Checagem de prontidão: as dependências de dados respondem? Usada pelo `/health/ready` (e serve a
qualquer outra porta de entrada que queira o mesmo diagnóstico)."""

from contextlib import suppress

from app.infra.mongo import mongo
from app.infra.redis.connection import redis


def checar_dependencias() -> dict[str, bool]:
    """`{dependência: respondeu}`. Para na primeira que falha: as seguintes ficam `False`."""

    checks = {"redis": False, "mongo": False}

    with suppress(Exception):
        redis.client.ping()
        checks["redis"] = True

        mongo.client.admin.command("ping")
        checks["mongo"] = True

    return checks


__all__ = ["checar_dependencias"]
