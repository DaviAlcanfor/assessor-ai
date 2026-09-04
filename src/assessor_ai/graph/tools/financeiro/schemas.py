# Essa classe garante que o objeto de Python passe todos esses campos

from pydantic import BaseModel, Field

from assessor_ai.graph.tools.financeiro.models import PaymentType


class AddTransactionArgs(BaseModel):
    amount: float = Field(..., description="Valor da transação (use positivo).")
    source_text: str = Field(..., description="Texto original do usuário.")
    occurred_at: str | None = Field(
        default=None,
        description="Timestamp ISO 8601; se ausente, usa NOW() no banco."
    )

    type_name: str | None = Field(default=None, description="Nome do tipo: INCOME | EXPENSES | TRANSFER.")
    category_id: int | None = Field(default=None, description="FK de categories (opcional).")
    category_name: str | None = Field(default=None, description="Nome da categoria entre as disponíveis: comida, besteira,  (opcional, usado para resolver category_id).")
    description: str | None = Field(default=None, description="Descrição (opcional).")
    payment_method: PaymentType | None = Field(default=None, description="Forma de pagamento (opcional).")



class QueryTransactionArgs(BaseModel):
    date_from_local: str | None = Field(default=None, description="Data local (America/Sao_Paulo) inicial para filtrar transações.")
    date_to_local: str | None = Field(default=None, description="Data local (America/Sao_Paulo) final para filtrar transações.")
    type_name: str | None = Field(default=None, description="Tipo da transação: INCOME | EXPENSES | TRANSFER.")
    source_text: str | None = Field(default=None, description="Texto para buscar em source_text ou description (filtro de texto).")
    
    

class UpdateTransactionArgs(BaseModel):
    id: int | None = Field(
        default=None,
        description="ID da transação a atualizar. Se ausente, será feita uma busca por (match_text + date_local)."
    )
    match_text: str | None = Field(
        default=None,
        description="Texto para localizar transação quando id não for informado (busca em source_text/description)."
    )
    date_local: str | None = Field(
        default=None,
        description="Data local (YYYY-MM-DD) em America/Sao_Paulo; usado em conjunto com match_text quando id ausente."
    )
    amount: float | None = Field(default=None, description="Novo valor.")
    type_name: str | None = Field(default=None, description="Novo type_name: INCOME | EXPENSES | TRANSFER.")
    category_id: int | None = Field(default=None, description="Nova categoria (id).")
    category_name: str | None = Field(default=None, description="Nova categoria (nome).")
    description: str | None = Field(default=None, description="Nova descrição.")
    payment_method: PaymentType | None = Field(default=None, description="Novo meio de pagamento.")
    occurred_at: str | None = Field(default=None, description="Novo timestamp ISO 8601.")

 