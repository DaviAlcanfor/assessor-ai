from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, Text, text
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


class TransactionType(Base):
    __tablename__ = "transaction_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(Text)


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
    type: Mapped[int] = mapped_column(ForeignKey("transaction_types.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    payment_method: Mapped[str | None]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_text: Mapped[str] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), default=LEGACY_USER_ID)

    transaction_type: Mapped["TransactionType"] = relationship()
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


__all__ = ["Base", "Category", "Event", "Transaction", "TransactionType", "User"]
