from langchain.agents import create_agent

from assessor_ai.graph.agents.prompts.loader import load_prompt
from assessor_ai.graph.llm import llm_especialista, llm_rapido
from assessor_ai.graph.tools import (
    AGENDA_TOOLS,
    FAQ_TOOLS,
    FINANCEIRO_TOOLS,
)

router_app = create_agent(
    model=llm_rapido,
    system_prompt=load_prompt("router"),
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=FINANCEIRO_TOOLS,
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