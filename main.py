from functools import partial
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from enum import StrEnum
from typing import Optional

from tools import TOOLS
from agents.router import RouterAgent
from agents.financeiro import FinanceiroAgent
from agents.agenda import AgendaAgent
from agents.orquestrador import OrquestradorAgent
from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY
)


# TODO isso vira uma classe depois pq vai usar em outros lugares sera?

# Fluxo:
# 1. Criar as LLMs (com suas chaves, modelos e configurações específicas)
# 2. Criar os agentes, associando cada um à sua LLM, prompt e ferramentas (se necessário)
# 3. Uso:
#    a) Receber input do usuário
#    b) Enviar para o Router, que decide a rota e pode responder diretamente ou encaminhar para um especialista
#    c) Se encaminhado para especialista, receber a resposta do especialista e enviar para o Orquestrador
#    d) Orquestrador formata a resposta final para o usuário


# Criando as LLMs
# (algumas informações como top_p não são customizáveis em certos modelos, como no ChatGroq)


class Model(StrEnum):
    GEMINI_2_5_FLASH    = "gemini-2.5-flash"
    LLAMA_3_3_VERSATILE = "llama-3.3-70b-versatile"
    QWEN_2_5_PRO        = "qwen-2.5-pro"
    CLAUDE_HAIKU        = "claude-haiku-4-5-20251001"
    CLAUDE_SONNET       = "claude-sonnet-4-6"


PROVIDER_MAP = {
    Model.GEMINI_2_5_FLASH:    "gemini",
    Model.LLAMA_3_3_VERSATILE: "groq",
    Model.QWEN_2_5_PRO:        "groq",
    Model.CLAUDE_HAIKU:        "claude",
    Model.CLAUDE_SONNET:       "claude",
}

API_KEYS = {
    "gemini": GEMINI_API_KEY,
    "groq":   GROQ_API_KEY,
    "claude": ANTHROPIC_API_KEY,
}

BUILDERS = {
    "gemini": ChatGoogleGenerativeAI,
    "groq":   ChatGroq,
    "claude": ChatAnthropic,
}


def build_llm(
    temperature: float,
    top_p: Optional[float] = None,
    model: Optional[str] = None
) -> ChatGoogleGenerativeAI | ChatGroq | ChatAnthropic:
    """
    Cria uma LLM com base no modelo informado.
    top_p só é aplicado para modelos Gemini.
    """

    provider = PROVIDER_MAP.get(model)
    
    if provider is None:
        raise ValueError(f"Modelo desconhecido: {model}")

    kwargs = dict(
        model=model,
        temperature=temperature,
        api_key=API_KEYS.get(provider),
    )

    # se fizer somente if top_p e valor dele seja 0.0, o python interpreta como False (mto legal)
    if top_p is not None and provider == "gemini":
        kwargs["top_p"] = top_p

    return BUILDERS[provider](**kwargs)


llm_gemini = build_llm(model=Model.GEMINI_2_5_FLASH, temperature=0.7, top_p=0.95)
llm_groq   = build_llm(model=Model.LLAMA_3_3_VERSATILE, temperature=0.7)
llm_rapido = build_llm(model=Model.LLAMA_3_3_VERSATILE, temperature=0.0)
llm_especialista = llm_gemini.with_fallbacks([llm_groq])


# Criando os agentes

router_app = create_agent(
    model=llm_rapido,
    tools=TOOLS,
    system_prompt=RouterAgent.PROMPT,
    checkpointer=MemorySaver()
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=TOOLS,
    system_prompt=FinanceiroAgent.PROMPT
)

agenda_app = create_agent(
    model=llm_rapido,
    system_prompt=AgendaAgent.PROMPT
)

orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=OrquestradorAgent.PROMPT,
)


# lógica principal dos agentes

EXECUTORES = {
    "financeiro": financeiro_app,
    "agenda": agenda_app,
}


def _build_config(session_id=None):
    return {
        "configurable": {
            "thread_id": session_id
        }
    }


def invoke_agent(agent , content: str, config: dict) -> str:
    resposta = agent.invoke(
        {"messages": [
            {"role": "user", 
            "content": content}
        ]},
        config=config
    )
    return resposta["messages"][-1].text



def get_route_from_response(response: str) -> str:
    """
    Extrai a rota do response do router.
    Retorna None se não houver ROUTE= na resposta.
    """
    if "ROUTE=" in response:
        route = response.split("ROUTE=")[1].split()[0].lower()
        return route
    # retorna None se não houver rota


def executar_fluxo_agente(user_input: str, session_id: str = None) -> str:
    """
    Executa o fluxo completo: router → especialista → orquestrador.
    Se o router responder diretamente (sem ROUTE=), retorna a resposta dele.
    """
    config = _build_config(session_id)
    invoke = partial(invoke_agent, config=config)
    
    resposta_router = invoke(router_app, user_input)

    if "ROUTE" not in resposta_router:
        return resposta_router

    route = get_route_from_response(resposta_router)
    agente_app = EXECUTORES.get(route)

    if agente_app is None:
        return f"Especialista para '{route}' não disponível."

    resposta_especialista = invoke(agente_app, resposta_router) 
    return invoke(orquestrador_app, resposta_especialista)



# TODO implementar frontend? 
def main():
    while True:
        try:
            user_input = input("👤 > ")
            
            resposta = executar_fluxo_agente(user_input, 
                                             session_id="id")    
            print("🤖 > ", resposta)
        
        except KeyboardInterrupt:
            print("\nAté logo!")
            break
        
        except Exception as e:
            print("Erro ao consumir API:", e)


if __name__ == "__main__":
    main()
