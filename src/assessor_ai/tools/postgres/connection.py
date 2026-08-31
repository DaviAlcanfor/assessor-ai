from contextlib import contextmanager
from contextvars import ContextVar, Token
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from assessor_ai.tools.postgres.models import LEGACY_USER_ID
from config.settings import settings

_engine = None
_SessionFactory = None
_pool: AsyncConnectionPool | None = None

# ponytail: ContextVar em vez de passar user_id manualmente por toda chamada de tool do
# LangChain (que só recebe os args escolhidos pelo LLM) — setado uma vez por request em
# chat/runner.py:executar, lido pelas tools de financeiro/agenda. Upgrade se o projeto
# passar a rodar tools fora de um único invoke síncrono por request (ex. fan-out paralelo
# de sub-agentes por usuários diferentes no mesmo processo).
_current_user_id: ContextVar[UUID] = ContextVar("current_user_id", default=LEGACY_USER_ID)


def set_current_user(user_id: UUID | str) -> Token:
    return _current_user_id.set(UUID(str(user_id)))


def reset_current_user(token: Token) -> None:
    _current_user_id.reset(token)


def current_user_id() -> UUID:
    return _current_user_id.get()


def _get_session_factory() -> sessionmaker:

    global _engine, _SessionFactory

    if _SessionFactory is None:
        _engine = create_engine(settings.POSTGRES_URL, pool_size=10)
        _SessionFactory = sessionmaker(bind=_engine)

    return _SessionFactory


async def get_checkpointer_pool() -> AsyncConnectionPool:
    """
    Pool async psycopg3 usado só pelo checkpointer do LangGraph (`graph/builder.py`), em paralelo
    ao engine SQLAlchemy acima, que continua em psycopg2 síncrono — unificar os dois drivers é PR
    à parte. `autocommit` e `dict_row` são exigência do `AsyncPostgresSaver`: sem o primeiro o
    `setup()` não persiste as tabelas, sem o segundo ele quebra ao ler as linhas.

    `open=False` + `await open()` porque o psycopg3 desencoraja abrir o pool no construtor (o
    pool async precisa do event loop que já está rodando).
    """

    global _pool

    if _pool is None:
        _pool = AsyncConnectionPool(
            settings.POSTGRES_URL,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=False,
        )
        await _pool.open()

    return _pool


async def dispose_engine() -> None:
    global _engine, _SessionFactory, _pool

    if _engine is not None:
        _engine.dispose()

    if _pool is not None:
        await _pool.close()

    _engine = None
    _SessionFactory = None
    _pool = None


@contextmanager
def get_session():

    session: Session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    assert current_user_id() == LEGACY_USER_ID

    outro = UUID("11111111-1111-1111-1111-111111111111")
    token = set_current_user(outro)
    assert current_user_id() == outro

    reset_current_user(token)
    assert current_user_id() == LEGACY_USER_ID

    print("current_user_id context isolation OK")
