from langchain.agents import create_agent

from app.graph.llm import llm_especialista, llm_rapido
from app.graph.prompts.loader import load_prompt
from app.graph.tools import (
    AGENDA_TOOLS,
    FAQ_TOOLS,
    FINANCEIRO_TOOLS,
    MERCADO_TOOLS,
    PERFIL_TOOLS,
)

router_app = create_agent(
    model=llm_rapido,
    system_prompt=load_prompt("router"),
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=FINANCEIRO_TOOLS + PERFIL_TOOLS + MERCADO_TOOLS,
    system_prompt=load_prompt("financeiro"),
)

agenda_app = create_agent(
    model=llm_especialista,
    tools=AGENDA_TOOLS,
    system_prompt=load_prompt("agenda"),
)

orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=load_prompt("orquestrador"),
)

faq_app = create_agent(
    model=llm_rapido,
    tools=FAQ_TOOLS,
    system_prompt=load_prompt("faq"),
)


__all__ = [
    "agenda_app",
    "faq_app",
    "financeiro_app",
    "orquestrador_app",
    "router_app",
]