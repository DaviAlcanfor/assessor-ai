"""
Uma pasta por feature (`financeiro`, `agenda`, `faq`, `chats`, `usuarios`), não por banco —
`usuarios` sozinho fala com Mongo, Postgres e Redis. As conexões, que são compartilhadas entre
features, ficam em `infra/`.

Cada feature expõe um `*Repo`. Os que têm tools do LLM (financeiro, agenda, faq) devolvem a lista
via `as_tools()`; os internos (chats, usuarios) são só chamados por `repositories/`.

As instâncias abaixo são singletons de processo: o construtor só guarda a conexão (que por sua vez
é lazy), então criá-las no import não abre socket nenhum.
"""

from assessor_ai.graph.tools.agenda.repo import AgendaRepo
from assessor_ai.graph.tools.faq.repo import FaqRepo
from assessor_ai.graph.tools.financeiro.repo import FinanceiroRepo
from assessor_ai.graph.tools.perfil.repo import PerfilRepo
from assessor_ai.graph.tools.usuarios.repo import UsuariosRepo

financeiro = FinanceiroRepo()
agenda     = AgendaRepo()
faq        = FaqRepo()
usuarios   = UsuariosRepo()
perfil     = PerfilRepo()

FINANCEIRO_TOOLS = financeiro.as_tools()
AGENDA_TOOLS     = agenda.as_tools()
FAQ_TOOLS        = faq.as_tools()
PERFIL_TOOLS     = perfil.as_tools()

# ChatsRepo importado por último, de propósito: `chats/helpers.py` importa
# `graph.agents.prompts.loader`, o que executa `graph/agents/__init__.py` — e esse módulo importa
# AGENDA_TOOLS/FAQ_TOOLS/FINANCEIRO_TOOLS/PERFIL_TOOLS deste mesmo módulo, que nesse ponto ainda
# está no meio da própria inicialização. Com o import de ChatsRepo antes destas atribuições, um
# `python main.py api` quebra com "cannot import name ... from partially initialized module".
from assessor_ai.graph.tools.chats.repo import ChatsRepo

chats = ChatsRepo()

__all__ = [
    "AGENDA_TOOLS",
    "FAQ_TOOLS",
    "FINANCEIRO_TOOLS",
    "PERFIL_TOOLS",
    "agenda",
    "chats",
    "faq",
    "financeiro",
    "perfil",
    "usuarios",
]
