from uuid import UUID

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa compartilhada — cada domínio declara seus models sobre ela."""


# Usuário "legado" criado pela migration a83e50c95f94 — mesmo propósito do DEFAULT da
# coluna no banco. Precisa ser setado explicitamente porque o ORM sempre manda a coluna
# no INSERT (diferente do SQL cru, que a omite e deixa o Postgres aplicar o DEFAULT).
LEGACY_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


__all__ = ["LEGACY_USER_ID", "Base"]
