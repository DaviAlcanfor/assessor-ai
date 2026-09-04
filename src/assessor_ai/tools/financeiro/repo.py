from datetime import UTC, datetime
from decimal import Decimal

from langchain_core.tools import StructuredTool
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from assessor_ai.core.logging import get_logger
from assessor_ai.tools.financeiro.models import (
    Category,
    PaymentType,
    Transaction,
    TransactionType,
)
from assessor_ai.tools.financeiro.schemas import (
    AddTransactionArgs,
    QueryTransactionArgs,
    UpdateTransactionArgs,
)
from assessor_ai.tools.infra.postgres import (
    PostgresRepo,
    local_date_filter,
    local_date_range_filter,
    transacional,
)
from assessor_ai.tools.response import Response

_TYPE_ALIASES: dict[str, list[str]] = {
    "INCOME":   ["GANHO", "RENDA", "ENTRADA"],
    "EXPENSES": ["DESPESA", "GASTO", "EXPENSE"],
    "TRANSFER": ["MANDEI", "TRANSFER", "ENVIO"],
}

_SALDO = func.sum(
    case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)
) - func.sum(
    case((Transaction.type == TransactionType.EXPENSES, Transaction.amount), else_=0)
)


def resolve_transaction_type(type_name: str | None) -> TransactionType:
    """
    Resolve o tipo de transação a partir de um nome livre (aceita aliases em
    português, ex: "GASTO" → EXPENSES). Sem argumento, retorna o tipo padrão
    (EXPENSES). Puramente em Python — não depende de lookup em tabela.
    """

    if not type_name:
        return TransactionType.EXPENSES

    t = type_name.strip().upper()

    for main_type, aliases in _TYPE_ALIASES.items():
        if t == main_type or t in aliases:
            return TransactionType(main_type)

    return TransactionType.EXPENSES


def _serializar(t: Transaction) -> dict:
    return {
        "id":             t.id,
        "amount":         float(t.amount),
        "type":           t.type,
        "category_id":    t.category_id,
        "description":    t.description,
        "payment_method": t.payment_method,
        "occurred_at":    str(t.occurred_at),
    }


class FinanceiroRepo(PostgresRepo):
    """
    Transações financeiras do usuário do turno. Cada método público é uma tool do agente
    financeiro — `@transacional` cuida da sessão, do commit/rollback e de converter exceção
    em `Response.error`, então o corpo fica só com a query.
    """

    log = get_logger("pg_financeiro")

    def _category_id(self, s: Session, category_name: str | None) -> int | None:
        """ID da categoria pelo nome, case-insensitive. None se não vier nome ou não existir."""

        if not category_name:
            return None

        return s.scalar(
            select(Category.id).where(func.lower(Category.name) == category_name.lower())
        )

    @transacional
    def add_transaction(
        self,
        s: Session,
        amount: float,
        source_text: str,
        occurred_at: str | None = None,
        type_name: str | None = None,
        category_id: int | None = None,
        description: str | None = None,
        payment_method: PaymentType | None = None,
        category_name: str | None = None,
    ) -> dict:
        """
        Insere uma transação financeira no banco de dados.

        O tipo é informado por nome (type_name). Aliases em português são aceitos:
        'GASTO' → EXPENSES, 'GANHO' → INCOME. Se nenhum tipo for fornecido, assume
        EXPENSES por padrão.

        A categoria pode ser informada por ID (category_id) ou nome (category_name).
        Se occurred_at não for informado, usa o timestamp atual do servidor.
        """

        tx = Transaction(
            amount=amount,
            type=resolve_transaction_type(type_name),
            category_id=category_id or self._category_id(s, category_name),
            description=description,
            payment_method=payment_method,
            occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(UTC),
            source_text=source_text,
            user_id=self.usuario,
        )
        s.add(tx)
        s.flush()

        return Response.ok(id=tx.id, occurred_at=str(tx.occurred_at))

    @transacional
    def total_balance(self, s: Session) -> dict:
        """Retorna o saldo total do usuário (INCOME - EXPENSES)."""

        resultado = s.scalar(select(_SALDO).where(Transaction.user_id == self.usuario))

        return Response.ok(amount=float(resultado) if resultado is not None else 0.0)

    @transacional
    def daily_balance(self, s: Session, date_local: str) -> dict:
        """
        Retorna o saldo líquido do usuário em um dia específico (INCOME - EXPENSES).

        date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
        """

        resultado = s.scalar(
            select(_SALDO).where(
                local_date_filter(Transaction.occurred_at, date_local),
                Transaction.user_id == self.usuario,
            )
        )

        return Response.ok(
            balance_date=date_local,
            total_balance=float(resultado) if resultado is not None else 0.0,
        )

    @transacional
    def query_transactions(
        self,
        s: Session,
        date_from_local: str | None = None,
        date_to_local: str | None = None,
        type_name: str | None = None,
        source_text: str | None = None,
    ) -> dict:
        """
        Consulta transações com filtros opcionais por data, tipo e texto.

        Quando date_from_local e date_to_local são informados juntos, retorna em ordem
        cronológica (ASC). Caso contrário, retorna as mais recentes primeiro (DESC).
        Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
        """

        stmt = select(Transaction).where(Transaction.user_id == self.usuario)

        if date_from_local and date_to_local:
            stmt = stmt.where(
                local_date_range_filter(Transaction.occurred_at, date_from_local, date_to_local)
            ).order_by(Transaction.occurred_at.asc())
        else:
            stmt = stmt.order_by(Transaction.occurred_at.desc())

        if type_name:
            stmt = stmt.where(Transaction.type == resolve_transaction_type(type_name))

        if source_text:
            like = f"%{source_text}%"
            stmt = stmt.where(
                or_(Transaction.source_text.ilike(like), Transaction.description.ilike(like))
            )

        transacoes = [_serializar(t) for t in s.scalars(stmt).all()]

        return Response.ok(total_records=len(transacoes), transactions=transacoes)

    @transacional
    def update_transaction(
        self,
        s: Session,
        id: int | None = None,
        match_text: str | None = None,
        date_local: str | None = None,
        amount: float | None = None,
        type_name: str | None = None,
        category_id: int | None = None,
        category_name: str | None = None,
        description: str | None = None,
        payment_method: PaymentType | None = None,
        occurred_at: str | None = None,
    ) -> dict:
        """
        Atualiza campos de uma transação existente.

        Localização por ID direto (id) ou por texto + data (match_text + date_local).
        Quando localizada por texto, atualiza a ocorrência mais recente que combine.
        Pelo menos um campo de atualização deve ser fornecido.
        Retorna o registro atualizado completo após o commit.
        """

        if not any(
            [amount, type_name, category_id, category_name, description, payment_method, occurred_at]
        ):
            return Response.error("Nada para atualizar: forneça pelo menos um campo.")

        target_id = id

        if target_id is None:
            if not match_text or not date_local:
                return Response.error(
                    "Sem 'id': informe match_text E date_local para localizar o registro."
                )

            target_id = s.scalar(
                select(Transaction.id)
                .where(
                    or_(
                        func.unaccent(Transaction.source_text).ilike(func.unaccent(f"%{match_text}%")),
                        func.unaccent(Transaction.description).ilike(func.unaccent(f"%{match_text}%")),
                    ),
                    local_date_filter(Transaction.occurred_at, date_local),
                    Transaction.user_id == self.usuario,
                )
                .order_by(Transaction.occurred_at.desc())
                .limit(1)
            )
            if not target_id:
                return Response.error("Nenhuma transação encontrada para os filtros fornecidos.")

        tx = s.get(Transaction, target_id)
        if tx is None or tx.user_id != self.usuario:
            return Response.ok(rows_affected=0, id=target_id, updated=None)

        if amount is not None:         tx.amount = Decimal(str(amount))
        if type_name is not None:      tx.type = resolve_transaction_type(type_name)
        if description is not None:    tx.description = description
        if payment_method is not None: tx.payment_method = payment_method
        if occurred_at is not None:    tx.occurred_at = datetime.fromisoformat(occurred_at)

        resolved_category_id = category_id or self._category_id(s, category_name)
        if resolved_category_id is not None:
            tx.category_id = resolved_category_id

        s.flush()

        updated = _serializar(tx) | {
            "category":    tx.category.name if tx.category else None,
            "source_text": tx.source_text,
        }

        return Response.ok(rows_affected=1, id=target_id, updated=updated)

    def as_tools(self) -> list[StructuredTool]:
        """
        Liga os métodos ao LangChain. `from_function` numa instância (e não `@tool` no método)
        porque `@tool` roda no corpo da classe, quando `self` ainda está na assinatura — e o
        `self` vaza pro JSON schema que vai pro LLM.
        """

        return [
            StructuredTool.from_function(
                self.add_transaction, name="add_transaction", args_schema=AddTransactionArgs
            ),
            StructuredTool.from_function(self.total_balance, name="total_balance"),
            StructuredTool.from_function(self.daily_balance, name="daily_balance"),
            StructuredTool.from_function(
                self.query_transactions, name="query_transactions", args_schema=QueryTransactionArgs
            ),
            StructuredTool.from_function(
                self.update_transaction, name="update_transaction", args_schema=UpdateTransactionArgs
            ),
        ]


__all__ = ["FinanceiroRepo", "resolve_transaction_type"]
