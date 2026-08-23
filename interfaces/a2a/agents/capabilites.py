from a2a.types import AgentSkill

SKILLS = [
    AgentSkill(
        id="financas-e-agenda",
        name="Finanças e agenda pessoal",
        description=(
            "Registra e consulta transações financeiras, gerencia compromissos de agenda e "
            "responde perguntas de FAQ sobre o assistente."
        ),
        tags=["financas", "agenda", "faq"],
        examples=[
            "Quanto gastei em restaurantes esse mês?",
            "Marca uma reunião pra sexta às 15h",
        ],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    ),
]
