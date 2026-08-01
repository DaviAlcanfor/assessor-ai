from langchain.agents import create_agent

from agents.prompts.agenda import AgendaPrompts
from agents.prompts.faq import FaqPrompts
from agents.prompts.financeiro import FinanceiroPrompts
from agents.prompts.orquestrador import OrquestradorPrompts
from agents.prompts.router import RouterPrompts
from graph.llm import llm_especialista, llm_rapido
from tools import (
    AGENDA_TOOLS,
    FAQ_TOOLS,
    FINANCEIRO_TOOLS,
)

router_app = create_agent(
    model=llm_rapido,
    system_prompt=RouterPrompts.system_prompt(),
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=FINANCEIRO_TOOLS,
    system_prompt=FinanceiroPrompts.system_prompt()
)

agenda_app = create_agent(
    model=llm_especialista,
    tools=AGENDA_TOOLS,
    system_prompt=AgendaPrompts.system_prompt()
)

orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=OrquestradorPrompts.system_prompt(),
)

faq_app = create_agent(
    model=llm_rapido,
    tools=FAQ_TOOLS,
    system_prompt=FaqPrompts.system_prompt()
)


__all__ = [
    "agenda_app",
    "faq_app",
    "financeiro_app",
    "orquestrador_app",
    "router_app",
]
