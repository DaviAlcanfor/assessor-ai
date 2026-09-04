from a2a.types import AgentSkill

# O card anuncia as skills separadas pra discovery; o POST /a2a continua roteando
# pelo grafo inteiro (o router decide o domínio pela mensagem).
SKILLS = [
    AgentSkill(
        id="moneysaving",
        name="Controle de finanças pessoais",
        description=(
            "Registra e consulta transações, calcula saldo total e diário e filtra "
            "gastos por categoria e período."
        ),
        tags=["financas", "gastos", "saldo", "transacoes"],
        examples=[
            "Quanto gastei em restaurantes esse mês?",
            "Registra um gasto de 50 reais com mercado",
            "Qual é o meu saldo?",
        ],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    ),
    AgentSkill(
        id="agenda",
        name="Agenda pessoal",
        description="Cria, consulta e atualiza compromissos e eventos do calendário do usuário.",
        tags=["agenda", "compromissos", "calendario"],
        examples=[
            "Marca uma reunião pra sexta às 15h",
            "O que eu tenho amanhã?",
        ],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    ),
    AgentSkill(
        id="faq",
        name="FAQ sobre o assistente",
        description="Responde perguntas sobre o que o Assessor AI faz e como usá-lo.",
        tags=["faq", "ajuda"],
        examples=["O que você consegue fazer?"],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    ),
]
