"""Persistência das transações financeiras (Postgres), sem regra de negócio.

Cada método público é uma unidade de trabalho sob `@transacional`: localizar e alterar ficam na mesma
transação. O `user_id` é sempre explícito e todo SELECT/UPDATE filtra por ele — o service é quem o
resolve do `session_context()`. Quem fala com o LLM é `graph/tools/financeiro/tools.py`.
"""

from datetime import datetime
from decimal import Decimal
from typing import NotRequired, TypedDict
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.domain.errors import RegistroNaoEncontrado
from app.infra.postgres import (
    PostgresRepo,
    local_date_filter,
    local_date_range_filter,
    transacional,
)
from app.infra.postgres.models import (
    Category,
    PaymentType,
    Transaction,
    TransactionType,
)
from app.repositories.categoria_repository import CategoriaRecord

_SALDO = func.sum(
    case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)
) - func.sum(
    case((Transaction.type == TransactionType.EXPENSES, Transaction.amount), else_=0)
)


class NovaTransacao(TypedDict):
    """Dados que o service já normalizou (tipo resolvido, datas parseadas)."""

    amount:         float
    type:           TransactionType
    category_id:    int | None
    category_name:  str | None
    description:    str | None
    payment_method: PaymentType | None
    occurred_at:    datetime
    source_text:    str


class TransacaoCriada(TypedDict):
    id:          int
    occurred_at: str


class TransacaoRecord(TypedDict):
    id:             int
    amount:         float
    type:           TransactionType
    category_id:    int | None
    description:    str | None
    payment_method: PaymentType | None
    occurred_at:    str


class TransacaoAtualizada(TransacaoRecord):
    category:    str | None
    source_text: str


class FiltrosTransacao(TypedDict):
    date_from_local: NotRequired[str | None]
    date_to_local:   NotRequired[str | None]
    type:            NotRequired[TransactionType | None]
    source_text:     NotRequired[str | None]


class CamposTransacao(TypedDict):
    """Só o que o usuário pediu pra mudar; ausente = não mexe."""

    amount:         NotRequired[float]
    type:           NotRequired[TransactionType]
    category_id:    NotRequired[int | None]
    category_name:  NotRequired[str | None]
    description:    NotRequired[str]
    payment_method: NotRequired[PaymentType]
    occurred_at:    NotRequired[datetime]


def _serializar(t: Transaction) -> TransacaoRecord:
    return {
        "id":             t.id,
        "amount":         float(t.amount),
        "type":           t.type,
        "category_id":    t.category_id,
        "description":    t.description,
        "payment_method": t.payment_method,
        "occurred_at":    str(t.occurred_at),
    }


def _categoria_id(s: Session, category_name: str | None) -> int | None:
    """ID da categoria pelo nome, case-insensitive. None se não vier nome ou não existir."""

    if not category_name:
        return None

    return s.scalar(select(Category.id).where(func.lower(Category.name) == category_name.lower()))


def _id_por_texto(s: Session, user_id: UUID, match_text: str, date_local: str) -> int | None:
    return s.scalar(
        select(Transaction.id)
        .where(
            or_(
                func.unaccent(Transaction.source_text).ilike(func.unaccent(f"%{match_text}%")),
                func.unaccent(Transaction.description).ilike(func.unaccent(f"%{match_text}%")),
            ),
            local_date_filter(Transaction.occurred_at, date_local),
            Transaction.user_id == user_id,
        )
        .order_by(Transaction.occurred_at.desc())
        .limit(1)
    )


class FinanceiroRepository(PostgresRepo):
    @transacional
    def categorias(self, s: Session) -> list[CategoriaRecord]:
        """Categorias que existem de verdade (tabela global): o service resolve o nome livre do LLM contra elas."""

        return [
            CategoriaRecord(id=c.id, name=c.name, description=c.description)
            for c in s.scalars(select(Category).order_by(Category.name)).all()
        ]

    @transacional
    def adicionar(self, s: Session, user_id: UUID, dados: NovaTransacao) -> TransacaoCriada:
        tx = Transaction(
            amount=dados["amount"],
            type=dados["type"],
            category_id=dados["category_id"] or _categoria_id(s, dados["category_name"]),
            description=dados["description"],
            payment_method=dados["payment_method"],
            occurred_at=dados["occurred_at"],
            source_text=dados["source_text"],
            user_id=user_id,
        )
        s.add(tx)
        s.flush()

        return {"id": tx.id, "occurred_at": str(tx.occurred_at)}

    @transacional
    def saldo_total(self, s: Session, user_id: UUID) -> float:
        resultado = s.scalar(select(_SALDO).where(Transaction.user_id == user_id))

        return float(resultado) if resultado is not None else 0.0

    @transacional
    def saldo_do_dia(self, s: Session, user_id: UUID, date_local: str) -> float:
        resultado = s.scalar(
            select(_SALDO).where(
                local_date_filter(Transaction.occurred_at, date_local),
                Transaction.user_id == user_id,
            )
        )

        return float(resultado) if resultado is not None else 0.0

    @transacional
    def consultar(self, s: Session, user_id: UUID, filtros: FiltrosTransacao) -> list[TransacaoRecord]:
        """Com período completo (de/até) vem em ordem cronológica; senão, as mais recentes primeiro."""

        stmt = select(Transaction).where(Transaction.user_id == user_id)

        de, ate = filtros.get("date_from_local"), filtros.get("date_to_local")
        if de and ate:
            stmt = stmt.where(local_date_range_filter(Transaction.occurred_at, de, ate)).order_by(
                Transaction.occurred_at.asc()
            )
        else:
            stmt = stmt.order_by(Transaction.occurred_at.desc())

        if tipo := filtros.get("type"):
            stmt = stmt.where(Transaction.type == tipo)

        if texto := filtros.get("source_text"):
            like = f"%{texto}%"
            stmt = stmt.where(
                or_(
                    func.unaccent(Transaction.source_text).ilike(func.unaccent(like)),
                    func.unaccent(Transaction.description).ilike(func.unaccent(like)),
                )
            )

        return [_serializar(t) for t in s.scalars(stmt).all()]

    @transacional
    def atualizar(
        self,
        s: Session,
        user_id: UUID,
        transacao_id: int | None,
        match_text: str | None,
        date_local: str | None,
        campos: CamposTransacao,
    ) -> TransacaoAtualizada | None:
        """Localiza por `transacao_id` ou, sem ele, por texto + dia (a mais recente que combine) e
        atualiza. `None` = o id não existe ou é de outro usuário; sem combinação por texto, levanta
        `RegistroNaoEncontrado`. Localizar e gravar na mesma transação evita janela entre os dois."""

        alvo = transacao_id

        if alvo is None:
            assert match_text and date_local  # o service já validou
            alvo = _id_por_texto(s, user_id, match_text, date_local)
            if not alvo:
                raise RegistroNaoEncontrado("Nenhuma transação encontrada para os filtros fornecidos.")

        tx = s.get(Transaction, alvo)
        if tx is None or tx.user_id != user_id:
            return None

        if "amount" in campos:         tx.amount = Decimal(str(campos["amount"]))
        if "type" in campos:           tx.type = campos["type"]
        if "description" in campos:    tx.description = campos["description"]
        if "payment_method" in campos: tx.payment_method = campos["payment_method"]
        if "occurred_at" in campos:    tx.occurred_at = campos["occurred_at"]

        nova_categoria = campos.get("category_id") or _categoria_id(s, campos.get("category_name"))
        if nova_categoria is not None:
            tx.category_id = nova_categoria

        s.flush()

        return TransacaoAtualizada(
            **_serializar(tx),
            category=tx.category.name if tx.category else None,
            source_text=tx.source_text,
        )


financeiro_repository = FinanceiroRepository()


__all__ = [
    "CamposTransacao",
    "FiltrosTransacao",
    "FinanceiroRepository",
    "NovaTransacao",
    "TransacaoAtualizada",
    "TransacaoCriada",
    "TransacaoRecord",
    "financeiro_repository",
]
