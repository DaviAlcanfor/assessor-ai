"""baseline schema

Revision ID: 1ae7bbffb913
Revises:
Create Date: 2026-07-30 11:16:58.437399

Reconstrói o schema do Postgres que já existia antes do Alembic (criado
manualmente, fora de qualquer migration): transaction_types, categories,
transactions, events.

Esta migration serve para ambientes NOVOS (`alembic upgrade head` cria tudo
do zero). O banco de dev já tinha essas tabelas populadas antes desta
migration existir — nele, em vez de `upgrade`, rodar:

    alembic stamp 1ae7bbffb913

para marcar o banco como já estando nesta revisão sem reexecutar o DDL
(evita "relation already exists").
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1ae7bbffb913'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    op.execute("""
        CREATE TABLE transaction_types (
            id   SERIAL PRIMARY KEY,
            type TEXT NOT NULL
        );
    """)
    op.execute("""
        INSERT INTO transaction_types (id, type) VALUES
            (1, 'INCOME'),
            (2, 'EXPENSES'),
            (3, 'TRANSFER');
    """)
    op.execute("SELECT setval('transaction_types_id_seq', 3);")

    op.execute("""
        CREATE TABLE categories (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(64) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        INSERT INTO categories (id, name) VALUES
            (1,  'comida'),
            (2,  'besteira'),
            (3,  'estudo'),
            (4,  'férias'),
            (5,  'transporte'),
            (6,  'moradia'),
            (7,  'saúde'),
            (8,  'lazer'),
            (9,  'contas'),
            (10, 'investimento'),
            (11, 'presente'),
            (12, 'outros');
    """)
    op.execute("SELECT setval('categories_id_seq', 12);")

    op.execute("""
        CREATE TABLE transactions (
            id             BIGSERIAL PRIMARY KEY,
            amount         NUMERIC(14, 2) NOT NULL,
            type           INTEGER NOT NULL DEFAULT 2
                               REFERENCES transaction_types(id),
            category_id    INTEGER
                               REFERENCES categories(id) ON DELETE SET NULL,
            description    TEXT,
            payment_method VARCHAR(32),
            occurred_at    TIMESTAMPTZ NOT NULL,
            source_text    TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE INDEX idx_transactions_category_time
            ON transactions (category_id, occurred_at DESC);
    """)
    op.execute("""
        CREATE INDEX idx_transactions_localday
            ON transactions (
                ((occurred_at AT TIME ZONE 'America/Sao_Paulo')::date)
            );
    """)
    op.execute("""
        CREATE INDEX idx_transactions_occurred_at
            ON transactions (occurred_at DESC);
    """)

    op.execute("""
        CREATE TABLE events (
            id           BIGSERIAL PRIMARY KEY,
            title        TEXT NOT NULL,
            start_time   TIMESTAMPTZ NOT NULL,
            end_time     TIMESTAMPTZ,
            location     TEXT,
            notes        TEXT,
            recorded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            source_text  TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE INDEX idx_events_start_time
            ON events (start_time DESC);
    """)


def downgrade() -> None:
    """Downgrade schema."""

    op.execute("DROP TABLE IF EXISTS events;")
    op.execute("DROP TABLE IF EXISTS transactions;")
    op.execute("DROP TABLE IF EXISTS categories;")
    op.execute("DROP TABLE IF EXISTS transaction_types;")
    op.execute("DROP EXTENSION IF EXISTS unaccent;")
