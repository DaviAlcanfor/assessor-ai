"""
Conexão com o Postgres e a base dos repositórios que falam com ele.

`PostgresConn` guarda os dois clientes que o projeto usa — o engine SQLAlchemy síncrono (tools de
financeiro/agenda) e o pool async psycopg3 (checkpointer do LangGraph) — os dois lazy. `PostgresRepo`
+ `@transacional` tiram o `with session()` e o `try/except` de dentro de cada operação.
"""

import functools
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import (
    ColumnElement,
    ColumnExpressionArgument,
    Engine,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, sessionmaker

from app.infra.base import Conector
from app.settings import settings


def local_date(column: ColumnExpressionArgument[datetime]) -> ColumnElement[datetime]:
    # equivalente a: (column AT TIME ZONE 'America/Sao_Paulo')::date
    return func.date(func.timezone("America/Sao_Paulo", column))


def local_date_filter(
    column: ColumnExpressionArgument[datetime], date_local: str
) -> ColumnElement[bool]:
    return local_date(column) == date_local


def local_date_range_filter(
    column: ColumnExpressionArgument[datetime], date_from_local: str, date_to_local: str
) -> ColumnElement[bool]:
    return local_date(column).between(date_from_local, date_to_local)


class PostgresConn(Conector[Engine]):

    def __init__(self) -> None:
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] | None = None

    def conectar(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(settings.database.postgres_url.get_secret_value(), pool_size=10)
            self._session_factory = sessionmaker(bind=self._engine)

        return self._engine

    @property
    def _factory(self) -> sessionmaker[Session]:
        self.conectar()
        assert self._session_factory is not None

        return self._session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Commit no sucesso, rollback na exceção, close sempre."""

        session = self._factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def checkpointer_pool(self) -> AsyncConnectionPool[AsyncConnection[dict[str, Any]]]:

        if self._pool is None:
            self._pool = AsyncConnectionPool(
                settings.database.postgres_url.get_secret_value(),
                kwargs={"autocommit": True, "row_factory": dict_row},
                open=False,
                check=AsyncConnectionPool.check_connection,
            )
            await self._pool.open()

        return self._pool

    async def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

        if self._pool is not None:
            await self._pool.close()

        self._engine = None
        self._session_factory = None
        self._pool = None


postgres = PostgresConn()


def transacional[R](metodo: Callable[..., R]) -> Callable[..., R]:
    """Abre a sessão, passa como 1º argumento depois do `self` e faz commit no sucesso / rollback na
    exceção (que sobe intacta: quem quiser virar `Response.error` é a camada de tool, não a infra)."""

    @functools.wraps(metodo)
    def wrapper(self: "PostgresRepo", *args: Any, **kwargs: Any) -> R:
        with self.conn.session() as s:
            return metodo(self, s, *args, **kwargs)

    return wrapper


class PostgresRepo:
    """
    Base dos repositórios de Postgres: carrega a conexão que `@transacional` usa.

    A conexão entra pelo construtor pra o teste poder injetar outra (SQLite in-memory, ver
    `tests/conftest.py`) sem monkeypatch de módulo. O usuário dono dos dados NÃO é lido do contexto
    aqui: cada método recebe `user_id` explícito, e quem o resolve é o service.
    """

    def __init__(self, conn: PostgresConn | None = None) -> None:
        self.conn = conn or postgres


__all__ = [
    "PostgresConn",
    "PostgresRepo",
    "local_date",
    "local_date_filter",
    "local_date_range_filter",
    "postgres",
    "transacional",
]
