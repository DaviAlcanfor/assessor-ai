"""add users table

Revision ID: 28948ff7767a
Revises: 1ae7bbffb913
Create Date: 2026-07-30 11:17:51.325423

Tabela `users` enxuta: só o necessário para ligar o domínio financeiro/agenda
a um usuário. `id` é o MESMO UUID já gerado pela aplicação para o `user_id`
do Mongo (`tools/mongo/users/core.py`) — não um identificador desacoplado.
Dados "valiosos" de perfil (nome, email, profile) continuam só no Mongo.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '28948ff7767a'
down_revision: Union[str, Sequence[str], None] = '1ae7bbffb913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("""
        CREATE TABLE users (
            id         UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""

    op.execute("DROP TABLE IF EXISTS users;")
