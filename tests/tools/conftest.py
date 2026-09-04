import unicodedata
from contextlib import contextmanager
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from assessor_ai.graph.tools.agenda.models import (
    Event,  # noqa: F401  (registra a tabela no metadata)
)
from assessor_ai.graph.tools.agenda.repo import AgendaRepo
from assessor_ai.graph.tools.financeiro.models import Category, Transaction
from assessor_ai.graph.tools.financeiro.repo import FinanceiroRepo
from assessor_ai.graph.tools.usuarios.models import User
from assessor_ai.infra.postgres import LEGACY_USER_ID, Base


def _timezone_sqlite(tz_name: str, timestamp: str) -> str:
    """
    Emula `timezone(zone, ts)` do Postgres, usado por local_date/local_date_filter.
    SQLite não guarda offset (o driver grava datetime tz-aware como wall-clock puro),
    então reconstruímos como UTC antes de converter pro fuso pedido.
    """

    naive = datetime.fromisoformat(timestamp).replace(tzinfo=UTC)
    return naive.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S")


def _unaccent_sqlite(value: str | None) -> str | None:
    if value is None:
        return None

    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


@pytest.fixture
def db_session():
    """
    Sessão real sobre SQLite in-memory no lugar do Postgres — a infra hoje é só cloud
    (ver AGENTS.md), sem container local pra apontar em teste. `timezone`/`unaccent` são
    funções nativas do Postgres sem equivalente em SQLite, registradas aqui via
    `create_function` pra exercitar o mesmo SQL (`local_date_filter` etc.) que roda em
    produção, em vez de mockar a sessão e perder cobertura desse filtro — foi justamente
    esse filtro que já teve um bug de timezone real (ver TODO.md).
    """

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _registrar_funcoes(dbapi_connection, _):
        dbapi_connection.create_function("timezone", 2, _timezone_sqlite)
        dbapi_connection.create_function("unaccent", 1, _unaccent_sqlite)

    # Índice funcional usa sintaxe `AT TIME ZONE` (Postgres puro, sem equivalente em
    # SQLite) — irrelevante pra correção das queries testadas aqui, só existe pra
    # performance no banco real.
    Transaction.__table__.indexes = {
        idx for idx in Transaction.__table__.indexes if idx.name != "idx_transactions_localday"
    }
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.add(User(id=LEGACY_USER_ID, created_at=datetime.now(UTC)))
    session.commit()

    yield session
    session.close()


class ConnFake:
    """
    Devolve sempre a mesma sessão SQLite. Substitui o `PostgresConn` real via construtor do
    repo — antes isso era monkeypatch de `get_session` no módulo de cada tool.
    """

    def __init__(self, session):
        self._session = session

    @contextmanager
    def session(self):
        try:
            yield self._session
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise


@pytest.fixture
def financeiro(db_session) -> FinanceiroRepo:
    return FinanceiroRepo(conn=ConnFake(db_session))


@pytest.fixture
def agenda(db_session) -> AgendaRepo:
    return AgendaRepo(conn=ConnFake(db_session))


@pytest.fixture
def categoria(db_session):
    cat = Category(name="Mercado", created_at=datetime.now(UTC))
    db_session.add(cat)
    db_session.commit()
    return cat
