from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from assessor_ai.tools.infra.postgres import LEGACY_USER_ID, Base


class TransactionType(StrEnum):
    INCOME   = "INCOME"
    EXPENSES = "EXPENSES"
    TRANSFER = "TRANSFER"


class PaymentType(StrEnum):
    DINHEIRO       = "DINHEIRO"
    PIX            = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO  = "CARTAO_DEBITO"
    BOLETO         = "BOLETO"
    OUTRO          = "OUTRO"


# native_enum=True + create_type=False: os tipos `transaction_type`/`payment_type` já
# existem no Postgres (CREATE TYPE feito na migration) — o SQLAlchemy só deve referenciar,
# nunca tentar criar/dropar o tipo via metadata.
_transaction_type_enum = SAEnum(TransactionType, name="transaction_type", create_type=False)
_payment_type_enum = SAEnum(PaymentType, name="payment_type", create_type=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index(
            "idx_transactions_localday",
            text("((occurred_at AT TIME ZONE 'America/Sao_Paulo'::text))::date"),
        ),
    )

    # with_variant: SQLite só trata a PK como rowid alias (autoincrement) se o tipo
    # declarado for exatamente Integer — BigInteger puro quebra o insert sem id explícito
    # em teste (SQLite in-memory, ver tests/tools/conftest.py). Sem efeito no
    # Postgres real (continua BIGINT).
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    type: Mapped[TransactionType] = mapped_column(_transaction_type_enum, default=TransactionType.EXPENSES)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    payment_method: Mapped[PaymentType | None] = mapped_column(_payment_type_enum)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_text: Mapped[str] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), default=LEGACY_USER_ID)

    category: Mapped["Category | None"] = relationship()


# Índices existentes no schema (criados nas migrations Alembic) — declarados aqui pra
# --autogenerate não tentar dropá-los num diff futuro.
Index("idx_transactions_occurred_at", Transaction.occurred_at.desc())
Index("idx_transactions_category_time", Transaction.category_id, Transaction.occurred_at.desc())


__all__ = ["Category", "PaymentType", "Transaction", "TransactionType"]
