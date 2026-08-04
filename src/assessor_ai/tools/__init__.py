from .faq_tools import faq_retriever
from .postgres.agenda.core import (
    add_event,
    query_daily_events,
    query_events,
    update_event,
)
from .postgres.financeiro.core import (
    add_transaction,
    daily_balance,
    query_transactions,
    total_balance,
    update_transaction,
)
from .redis.api_key import get_user_id_by_api_key
from .redis.chat import can_send_message

REDIS_TOOLS = [get_user_id_by_api_key, can_send_message]
FINANCEIRO_TOOLS = [add_transaction, daily_balance, total_balance, query_transactions, update_transaction]
AGENDA_TOOLS = [add_event, query_daily_events, query_events, update_event]
FAQ_TOOLS = [faq_retriever]

__all__ = [
    "AGENDA_TOOLS",
    "FAQ_TOOLS",
    "FINANCEIRO_TOOLS",
    "REDIS_TOOLS"
]