"""
Conexão com o Postgres e a base dos repositórios que falam com ele.

`PostgresConn` guarda os dois clientes que o projeto usa — o engine SQLAlchemy síncrono (tools de
financeiro/agenda) e o pool async psycopg3 (checkpointer do LangGraph) — os dois lazy. `PostgresRepo`
+ `@transacional` tiram o `with session()` e o `try/except` de dentro de cada operação.
"""

import functools
import inspect
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime
from typing import Any
from uuid import UUID

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
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from assessor_ai.graph.tools.response import Response, ToolResponse
from assessor_ai.infra.base import Conector
from assessor_ai.logging import get_logger
from assessor_ai.privacy import anonimizar_entrada
from assessor_ai.settings import settings


def _redigir(valor: object) -> str:
    """Argumento de tool pode carregar PII (o LLM repassa o texto do usuário)."""

    texto, _ = anonimizar_entrada(str(valor))
    return texto


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


class Base(DeclarativeBase):
    """Base declarativa compartilhada — cada feature declara seus models sobre ela."""


# Usuário "legado" criado pela migration a83e50c95f94 — mesmo propósito do DEFAULT da
# coluna no banco. Precisa ser setado explicitamente porque o ORM sempre manda a coluna
# no INSERT (diferente do SQL cru, que a omite e deixa o Postgres aplicar o DEFAULT).
LEGACY_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# ponytail: ContextVar em vez de passar user_id manualmente por toda chamada de tool do
# LangChain (que só recebe os args escolhidos pelo LLM) — setado uma vez por request em
# services/runner.py:executar, lido pelos repositórios de financeiro/agenda. Upgrade se o
# projeto passar a rodar tools fora de um único invoke síncrono por request (ex. fan-out
# paralelo de sub-agentes por usuários diferentes no mesmo processo).
_current_user_id: ContextVar[UUID] = ContextVar("current_user_id", default=LEGACY_USER_ID)


def set_current_user(user_id: UUID | str) -> Token[UUID]:
    return _current_user_id.set(UUID(str(user_id)))


def reset_current_user(token: Token[UUID]) -> None:
    # ponytail: mesmo caso de identifiers.py:reset_usuario_atual — token criado num Context que
    # pode não ser mais o corrente quando um stream SSE órfão (conexão do cliente derrubada) é
    # fechado pelo asyncgen finalizer do event loop.
    try:
        _current_user_id.reset(token)
    except ValueError:
        pass


def current_user_id() -> UUID:
    return _current_user_id.get()


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


def transacional(metodo: Callable[..., ToolResponse]) -> Callable[..., ToolResponse]:

    @functools.wraps(metodo)
    def wrapper(self: "PostgresRepo", *args: Any, **kwargs: Any) -> ToolResponse:
        nome = metodo.__name__
        self.log.info("CHAMANDO | %s | %s", nome, _redigir(kwargs))
        inicio = time.perf_counter()

        with self.conn.session() as s:
            try:
                resultado = metodo(self, s, *args, **kwargs)
            except Exception as e:
                self.log.error("ERRO | %s | %s", nome, e)
                return Response.error(e)

        elapsed = time.perf_counter() - inicio
        self.log.info("OK | %s | status=%s | %.3fs", nome, resultado.get("status"), elapsed)

        return resultado

    assinatura = inspect.signature(metodo)
    wrapper.__signature__ = assinatura.replace(  # type: ignore[attr-defined]
        parameters=[p for nome, p in assinatura.parameters.items() if nome != "s"]
    )

    return wrapper


class PostgresRepo:
    """
    Base dos repositórios de Postgres: carrega a conexão e o logger que `@transacional` usa.

    A conexão entra pelo construtor pra o teste poder injetar outra (SQLite in-memory, ver
    `tests/tools/conftest.py`) sem monkeypatch de módulo.
    """

    log = get_logger("pg")

    def __init__(self, conn: PostgresConn | None = None) -> None:
        self.conn = conn or postgres

    @property
    def usuario(self) -> UUID:
        """
        Dono do turno atual. Toda query precisa filtrar por ele — não há filtro implícito
        (ver TODO.md: o fix estrutural pra isso é RLS no Postgres, não esperteza no ORM).
        """

        return current_user_id()


__all__ = [
    "LEGACY_USER_ID",
    "Base",
    "PostgresConn",
    "PostgresRepo",
    "current_user_id",
    "local_date",
    "local_date_filter",
    "local_date_range_filter",
    "postgres",
    "reset_current_user",
    "set_current_user",
    "transacional",
]
