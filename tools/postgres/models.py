from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Usuário "legado" criado pela migration a83e50c95f94 — mesmo propósito do DEFAULT da
# coluna no banco: financeiro/agenda ainda não propagam o user_id real (ver TODO.md).
# Precisa ser setado explicitamente aqui porque o ORM sempre manda a coluna no INSERT
# (diferente do SQL cru, que a omite e deixa o Postgres aplicar o DEFAULT).
LEGACY_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TransactionType(StrEnum):
    INCOME = "INCOME"
    EXPENSES = "EXPENSES"
    TRANSFER = "TRANSFER"


class PaymentType(StrEnum):
    DINHEIRO = "DINHEIRO"
    PIX = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    BOLETO = "BOLETO"
    OUTRO = "OUTRO"


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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    type: Mapped[TransactionType] = mapped_column(_transaction_type_enum, default=TransactionType.EXPENSES)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    payment_method: Mapped[PaymentType | None] = mapped_column(_payment_type_enum)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_text: Mapped[str] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), default=LEGACY_USER_ID)

    category: Mapped["Category | None"] = relationship()


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_text: Mapped[str] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), default=LEGACY_USER_ID)


# Índices existentes no schema (criados nas migrations Alembic) — declarados aqui pra
# --autogenerate não tentar dropá-los num diff futuro.
Index("idx_transactions_occurred_at", Transaction.occurred_at.desc())
Index("idx_transactions_category_time", Transaction.category_id, Transaction.occurred_at.desc())
Index("idx_events_start_time", Event.start_time.desc())


__all__ = ["Base", "Category", "Event", "PaymentType", "Transaction", "TransactionType", "User"]
