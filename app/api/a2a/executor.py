from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import InvalidParamsError, Message, Part, Role, TaskNotCancelableError

from app.api.a2a.sessions import sessoes
from app.domain.errors import LimiteDeMensagensExcedido
from app.services import chat_service


def _mensagem_agente(context_id: str, texto: str) -> Message:
    return Message(
        message_id=str(uuid4()),
        context_id=context_id,
        role=Role.ROLE_AGENT,
        parts=[Part(text=texto)],
    )


class AssessorAgentExecutor(AgentExecutor):
    """Ponte entre o protocolo A2A e `services/chat_service.py` — mesma camada usada por TUI/API."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # context_id é opcional no protocolo, mas é a chave da sessão aqui — sem ele não há
        # conversa pra continuar nem pra onde devolver a resposta.
        if context.context_id is None:
            raise InvalidParamsError(message="context_id é obrigatório.")

        texto = context.get_user_input()
        user_id, session_id = await sessoes.obter(context.context_id)

        try:
            resposta = await chat_service.send_message(user_id, session_id, texto)
        except LimiteDeMensagensExcedido as e:
            resposta = e.public_message

        await event_queue.enqueue_event(_mensagem_agente(context.context_id, resposta))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise TaskNotCancelableError()


__all__ = ["AssessorAgentExecutor"]
