"""add user_id fk to transactions and events

Revision ID: a83e50c95f94
Revises: 28948ff7767a
Create Date: 2026-07-30 11:18:44.946547

Adiciona `user_id` (FK -> users.id) em `transactions` e `events`.

Como essas tabelas já tinham linhas antes de existir um conceito de usuário,
a coluna é criada com backfill: um usuário "legado" é garantido em `users`,
as linhas existentes apontam pra ele, e só então a coluna vira NOT NULL.

O `DEFAULT` no usuário legado é intencional e temporário: as tools de
financeiro/agenda (`add_transaction`, `add_event`, etc.) ainda não passam
`user_id` explícito no INSERT (fora do escopo desta migration — é um
follow-up). Sem o default, esses INSERTs quebrariam por violação de NOT
NULL. Quando o follow-up passar a propagar o `user_id` real do agente, esse
`DEFAULT` deve ser removido.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a83e50c95f94'
down_revision: str | Sequence[str] | None = '28948ff7767a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Upgrade schema."""

    op.execute(f"""
        INSERT INTO users (id) VALUES ('{_LEGACY_USER_ID}')
        ON CONFLICT (id) DO NOTHING;
    """)

    for table in ("transactions", "events"):
        op.execute(f"""
            ALTER TABLE {table}
                ADD COLUMN user_id UUID
                    REFERENCES users(id)
                    DEFAULT '{_LEGACY_USER_ID}';
        """)
        op.execute(f"""
            UPDATE {table} SET user_id = '{_LEGACY_USER_ID}'
            WHERE user_id IS NULL;
        """)
        op.execute(f"""
            ALTER TABLE {table} ALTER COLUMN user_id SET NOT NULL;
        """)


def downgrade() -> None:
    """Downgrade schema."""

    for table in ("transactions", "events"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS user_id;")
