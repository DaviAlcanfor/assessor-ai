from langchain.agents import create_agent


from agents.prompts.router import RouterAgent
from agents.prompts.financeiro import FinanceiroAgent
from agents.prompts.agenda import AgendaAgent
from agents.prompts.orquestrador import OrquestradorAgent
from agents.prompts.faq import FaqAgent

from graph.llm import (
    llm_rapido,
    llm_especialista
)

from tools import (
    FINANCEIRO_TOOLS, 
    AGENDA_TOOLS,
    FAQ_TOOLS,
)


router_app = create_agent(
    model=llm_rapido,
    system_prompt=RouterAgent.PROMPT,
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=FINANCEIRO_TOOLS,
    system_prompt=FinanceiroAgent.PROMPT
)

agenda_app = create_agent(
    model=llm_especialista,
    tools=AGENDA_TOOLS,
    system_prompt=AgendaAgent.PROMPT
)

orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=OrquestradorAgent.PROMPT,
)

faq_app = create_agent(
    model=llm_rapido,
    tools=FAQ_TOOLS,
    system_prompt=FaqAgent.PROMPT
)


__all__ = [
    "router_app",
    "financeiro_app",
    "agenda_app",
    "orquestrador_app",    
    "faq_app",
]