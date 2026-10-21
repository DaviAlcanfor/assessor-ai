from typing import ClassVar

from app.domain.models.financeiro import PaymentType, TransactionType
from app.graph.tools.base import Schemas, ToolSet
from app.graph.tools.financeiro.schemas import (
    AddTransactionArgs,
    QueryTransactionArgs,
    UpdateTransactionArgs,
)
from app.graph.tools.response import Response, ToolResponse
from app.services.financeiro_service import FinanceiroService, financeiro_service


class FinanceiroTools(ToolSet):
    """Transações financeiras do usuário do turno. Cada método público é uma tool do agente financeiro;
    a regra e o acesso ao banco estão em `FinanceiroService`."""

    schemas: ClassVar[Schemas] = {
        "add_transaction": AddTransactionArgs,
        "query_transactions": QueryTransactionArgs,
        "update_transaction": UpdateTransactionArgs,
    }

    def __init__(self, service: FinanceiroService | None = None) -> None:
        self.service = service or financeiro_service

    async def add_transaction(
        self,
        amount: float,
        source_text: str,
        occurred_at: str | None = None,
        type_name: TransactionType | None = None,
        category_id: int | None = None,
        description: str | None = None,
        payment_method: PaymentType | None = None,
        category_name: str | None = None,
    ) -> ToolResponse:
        """
        Insere uma transação financeira no banco de dados.

        O tipo (type_name) é INCOME, EXPENSES ou TRANSFER; sem informar, assume EXPENSES.

        A categoria pode ser informada por ID (category_id) ou nome em linguagem natural
        (category_name): o sistema escolhe a categoria cadastrada que combina. A resposta traz
        `category` (a usada) e, se nenhuma combinou, um `aviso` para repassar ao usuário.
        Se occurred_at não for informado, usa o timestamp atual do servidor.
        """

        criada = await self.service.adicionar(
            amount=amount,
            source_text=source_text,
            occurred_at=occurred_at,
            type_name=type_name,
            category_id=category_id,
            category_name=category_name,
            description=description,
            payment_method=payment_method,
        )

        return Response.ok(**criada)

    async def total_balance(self) -> ToolResponse:
        """Retorna o saldo total do usuário (INCOME - EXPENSES)."""

        return Response.ok(amount=await self.service.saldo_total())

    async def daily_balance(self, date_local: str) -> ToolResponse:
        """
        Retorna o saldo líquido do usuário em um dia específico (INCOME - EXPENSES).

        date_local deve estar no formato YYYY-MM-DD, interpretado no fuso America/Sao_Paulo.
        """

        return Response.ok(balance_date=date_local, total_balance=await self.service.saldo_do_dia(date_local))

    async def query_transactions(
        self,
        date_from_local: str | None = None,
        date_to_local: str | None = None,
        type_name: TransactionType | None = None,
        source_text: str | None = None,
    ) -> ToolResponse:
        """
        Consulta transações com filtros opcionais por data, tipo e texto.

        Quando date_from_local e date_to_local são informados juntos, retorna em ordem
        cronológica (ASC). Caso contrário, retorna as mais recentes primeiro (DESC).
        Datas devem estar no formato YYYY-MM-DD, interpretadas no fuso America/Sao_Paulo.
        """

        transacoes = await self.service.consultar(date_from_local, date_to_local, type_name, source_text)

        return Response.ok(total_records=len(transacoes), transactions=transacoes)

    async def update_transaction(
        self,
        id: int | None = None,
        match_text: str | None = None,
        date_local: str | None = None,
        amount: float | None = None,
        type_name: TransactionType | None = None,
        category_id: int | None = None,
        category_name: str | None = None,
        description: str | None = None,
        payment_method: PaymentType | None = None,
        occurred_at: str | None = None,
    ) -> ToolResponse:
        """
        Atualiza campos de uma transação existente.

        Localização por ID direto (id) ou por texto + data (match_text + date_local).
        Quando localizada por texto, atualiza a ocorrência mais recente que combine.
        Pelo menos um campo de atualização deve ser fornecido.
        Retorna o registro atualizado completo após o commit.
        """

        atualizada = await self.service.atualizar(
            id=id,
            match_text=match_text,
            date_local=date_local,
            amount=amount,
            type_name=type_name,
            category_id=category_id,
            category_name=category_name,
            description=description,
            payment_method=payment_method,
            occurred_at=occurred_at,
        )

        if atualizada is None:
            return Response.ok(rows_affected=0, id=id, updated=None)

        return Response.ok(rows_affected=1, id=atualizada["id"], updated=atualizada)


__all__ = ["FinanceiroTools"]
