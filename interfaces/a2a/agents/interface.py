import asyncio
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role, TaskNotCancelableError

from assessor_ai.chat import service as chat_service

# ponytail: mapa em memória (perdido no restart, não compartilhado entre workers) — troca por
# Redis (mesmo padrão de tools/redis/chat.py) se o A2A rodar com múltiplos processos/instâncias
_sessoes: dict[str, tuple[str, str]] = {}


def _sessao_para(context_id: str) -> tuple[str, str]:
    if context_id not in _sessoes:
        _sessoes[context_id] = chat_service.iniciar_sessao()
    return _sessoes[context_id]


def _mensagem_agente(context_id: str, texto: str) -> Message:
    return Message(
        message_id=str(uuid4()),
        context_id=context_id,
        role=Role.ROLE_AGENT,
        parts=[Part(text=texto)],
    )


class AssessorAgentExecutor(AgentExecutor):
    """Ponte entre o protocolo A2A e chat/service.py — mesma camada usada por terminal/TUI/API."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        texto = context.get_user_input()
        user_id, session_id = _sessao_para(context.context_id)

        try:
            resposta = await asyncio.to_thread(
                chat_service.send_message, user_id, session_id, texto
            )
        except chat_service.LimiteDeMensagensExcedido as e:
            resposta = str(e)

        await event_queue.enqueue_event(_mensagem_agente(context.context_id, resposta))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise TaskNotCancelableError()
