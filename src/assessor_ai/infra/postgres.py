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
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import ColumnElement, Engine, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from assessor_ai.config import settings
from assessor_ai.graph.tools.response import Response
from assessor_ai.logging import get_logger
from assessor_ai.privacy import anonimizar_entrada


def _redigir(valor: Any) -> str:
    """Argumento de tool pode carregar PII (o LLM repassa o texto do usuário)."""

    texto, _ = anonimizar_entrada(str(valor))
    return texto


def local_date(column):
    """
    Expressão de data local (America/Sao_Paulo) a partir de uma coluna timestamptz.

    Equivalente a: (column AT TIME ZONE 'America/Sao_Paulo')::date
    """

    return func.date(func.timezone("America/Sao_Paulo", column))


def local_date_filter(column, date_local: str) -> ColumnElement[bool]:
    """Expressão booleana pra filtrar registros por uma data local específica."""

    return local_date(column) == date_local


def local_date_range_filter(
    column, date_from_local: str, date_to_local: str
) -> ColumnElement[bool]:
    """Expressão booleana pra filtrar registros por um intervalo de datas locais."""

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


def set_current_user(user_id: UUID | str) -> Token:
    return _current_user_id.set(UUID(str(user_id)))


def reset_current_user(token: Token) -> None:
    _current_user_id.reset(token)


def current_user_id() -> UUID:
    return _current_user_id.get()


class PostgresConn:
    """Engine e pool são criados no primeiro uso — nunca no import do módulo."""

    def __init__(self) -> None:
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._pool: AsyncConnectionPool | None = None

    @property
    def _factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            self._engine = create_engine(settings.POSTGRES_URL.get_secret_value(), pool_size=10)
            self._session_factory = sessionmaker(bind=self._engine)

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

    async def checkpointer_pool(self) -> AsyncConnectionPool:
        """
        Pool async psycopg3 usado só pelo checkpointer do LangGraph (`graph/builder.py`), em paralelo
        ao engine SQLAlchemy acima, que continua em psycopg2 síncrono — unificar os dois drivers é PR
        à parte. `autocommit` e `dict_row` são exigência do `AsyncPostgresSaver`: sem o primeiro o
        `setup()` não persiste as tabelas, sem o segundo ele quebra ao ler as linhas.

        `open=False` + `await open()` porque o psycopg3 desencoraja abrir o pool no construtor (o
        pool async precisa do event loop que já está rodando).
        """

        if self._pool is None:
            self._pool = AsyncConnectionPool(
                settings.POSTGRES_URL.get_secret_value(),
                kwargs={"autocommit": True, "row_factory": dict_row},
                open=False,
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


def transacional(metodo: Callable[..., Any]) -> Callable[..., Any]:
    """
    Abre a sessão, injeta como 2º argumento do método, faz commit/rollback e converte exceção
    em `Response.error` — o corpo do método fica só com a query.

    O ajuste de `__signature__` não é cosmético: `functools.wraps` sozinho faz o
    `inspect.signature` seguir `__wrapped__` e enxergar o parâmetro `s`, que então vaza pro JSON
    schema que o `StructuredTool` manda pro LLM (mesma classe de bug do `self` em `@tool` de
    método). Corrigir aqui vale pra toda tool, inclusive as que não passam `args_schema`.
    """

    @functools.wraps(metodo)
    def wrapper(self: "PostgresRepo", *args: Any, **kwargs: Any) -> dict:
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
