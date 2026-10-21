"""
As tools do LLM, uma pasta por domínio (`financeiro`, `agenda`, `mercado`, `perfil`, `faq`). Cada uma tem
`schemas.py` (o que o LLM vê) e `tools.py` (uma classe `ToolSet` fina: valida os argumentos, chama o
service e devolve `Response`). A regra e o acesso a dados ficam em `services/` e `repositories/`.

As instâncias abaixo são singletons de processo: o construtor só guarda o service, que por sua vez guarda
um repository com conexão lazy — criá-las no import não abre socket nenhum.
"""

from app.graph.tools.agenda.tools import AgendaTools
from app.graph.tools.faq.tools import FaqTools
from app.graph.tools.financeiro.tools import FinanceiroTools
from app.graph.tools.mercado.tools import MercadoTools
from app.graph.tools.perfil.tools import PerfilTools

financeiro = FinanceiroTools()
agenda     = AgendaTools()
mercado    = MercadoTools()
perfil     = PerfilTools()
faq        = FaqTools()

FINANCEIRO_TOOLS = financeiro.as_tools()
AGENDA_TOOLS     = agenda.as_tools()
MERCADO_TOOLS    = mercado.as_tools()
PERFIL_TOOLS     = perfil.as_tools()
FAQ_TOOLS        = faq.as_tools()

__all__ = [
    "AGENDA_TOOLS",
    "FAQ_TOOLS",
    "FINANCEIRO_TOOLS",
    "MERCADO_TOOLS",
    "PERFIL_TOOLS",
    "agenda",
    "faq",
    "financeiro",
    "mercado",
    "perfil",
]
