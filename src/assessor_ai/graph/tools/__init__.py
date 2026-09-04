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
from assessor_ai.graph.tools.chats.repo import ChatsRepo
from assessor_ai.graph.tools.faq.repo import FaqRepo
from assessor_ai.graph.tools.financeiro.repo import FinanceiroRepo
from assessor_ai.graph.tools.usuarios.repo import UsuariosRepo

financeiro = FinanceiroRepo()
agenda     = AgendaRepo()
faq        = FaqRepo()
chats      = ChatsRepo()
usuarios   = UsuariosRepo()

FINANCEIRO_TOOLS = financeiro.as_tools()
AGENDA_TOOLS     = agenda.as_tools()
FAQ_TOOLS        = faq.as_tools()

__all__ = [
    "AGENDA_TOOLS",
    "FAQ_TOOLS",
    "FINANCEIRO_TOOLS",
    "agenda",
    "chats",
    "faq",
    "financeiro",
    "usuarios",
]
