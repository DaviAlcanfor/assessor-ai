"""Models ORM do Postgres. Importar o pacote registra todas as tabelas no `Base.metadata` (o Alembic e
os testes dependem disso)."""

from app.infra.postgres.models.agenda import Event
from app.infra.postgres.models.base import LEGACY_USER_ID, Base
from app.infra.postgres.models.financeiro import (
    Category,
    PaymentType,
    Transaction,
    TransactionType,
)
from app.infra.postgres.models.identity import User

__all__ = [
    "LEGACY_USER_ID",
    "Base",
    "Category",
    "Event",
    "PaymentType",
    "Transaction",
    "TransactionType",
    "User",
]
