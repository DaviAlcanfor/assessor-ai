"""transaction_type and payment_type as native enums

Revision ID: 09b347fdbb3c
Revises: a83e50c95f94
Create Date: 2026-08-03 11:55:34.901641

Substitui a tabela de lookup `transaction_types` (consultada em runtime via
`resolve_type_id`) por um tipo nativo do Postgres (`CREATE TYPE ... AS ENUM`),
e faz o mesmo para `payment_method`, que até aqui era um VARCHAR(32) livre sem
nenhuma validação. Elimina o round-trip ao banco só pra resolver um ID de tipo
fixo (ver `tools/postgres/helpers.py:resolve_transaction_type`, agora puro
Python).

Sem dados a preservar: `transactions` está vazia em todos os ambientes atuais.
Ainda assim o `UPDATE ... USING` abaixo é escrito pra ser seguro caso existam
linhas — `type` mapeia os IDs fixos 1/2/3 (únicos que `transaction_types` já
teve desde a baseline), e `payment_method` mapeia só valores que já batem
exatamente com o enum novo (case-insensitive), descartando o resto pra NULL
em vez de falhar a migration.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '09b347fdbb3c'
down_revision: str | Sequence[str] | None = 'a83e50c95f94'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("CREATE TYPE transaction_type AS ENUM ('INCOME', 'EXPENSES', 'TRANSFER');")
    op.execute("""
        CREATE TYPE payment_type AS ENUM (
            'DINHEIRO', 'PIX', 'CARTAO_CREDITO', 'CARTAO_DEBITO', 'BOLETO', 'OUTRO'
        );
    """)

    op.execute("ALTER TABLE transactions ALTER COLUMN type DROP DEFAULT;")
    op.execute("ALTER TABLE transactions DROP CONSTRAINT transactions_type_fkey;")
    op.execute("""
        ALTER TABLE transactions
            ALTER COLUMN type TYPE transaction_type
            USING (
                CASE type
                    WHEN 1 THEN 'INCOME'
                    WHEN 2 THEN 'EXPENSES'
                    WHEN 3 THEN 'TRANSFER'
                END
            )::transaction_type;
    """)
    op.execute("ALTER TABLE transactions ALTER COLUMN type SET DEFAULT 'EXPENSES'::transaction_type;")

    op.execute("""
        ALTER TABLE transactions
            ALTER COLUMN payment_method TYPE payment_type
            USING (
                CASE
                    WHEN upper(payment_method) IN (
                        'DINHEIRO', 'PIX', 'CARTAO_CREDITO', 'CARTAO_DEBITO', 'BOLETO', 'OUTRO'
                    ) THEN upper(payment_method)
                    ELSE NULL
                END
            )::payment_type;
    """)

    op.execute("DROP TABLE transaction_types;")


def downgrade() -> None:
    """Downgrade schema."""

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

    op.execute("ALTER TABLE transactions ALTER COLUMN type DROP DEFAULT;")
    op.execute("""
        ALTER TABLE transactions
            ALTER COLUMN type TYPE INTEGER
            USING (
                CASE type::text
                    WHEN 'INCOME' THEN 1
                    WHEN 'EXPENSES' THEN 2
                    WHEN 'TRANSFER' THEN 3
                END
            );
    """)
    op.execute("ALTER TABLE transactions ALTER COLUMN type SET DEFAULT 2;")
    op.execute("""
        ALTER TABLE transactions
            ADD CONSTRAINT transactions_type_fkey
            FOREIGN KEY (type) REFERENCES transaction_types(id);
    """)

    op.execute("""
        ALTER TABLE transactions
            ALTER COLUMN payment_method TYPE VARCHAR(32)
            USING payment_method::text;
    """)

    op.execute("DROP TYPE payment_type;")
    op.execute("DROP TYPE transaction_type;")
