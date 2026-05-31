from .postgres.financeiro.core import (
    add_transaction, 
    daily_balance, 
    total_balance, 
    update_transaction, 
    query_transactions
)
from .postgres.agenda.core import (
    add_event,
    query_daily_events,
    query_events,
    update_event,
)

from .faq_tools import (
    faq_retriever
)

FINANCEIRO_TOOLS = [add_transaction, daily_balance, total_balance, query_transactions, update_transaction]
AGENDA_TOOLS = [add_event, query_daily_events, query_events, update_event]
FAQ_TOOLS = [faq_retriever]

__all__ = [
    "FINANCEIRO_TOOLS", 
    "AGENDA_TOOLS",
    "FAQ_TOOLS",
]