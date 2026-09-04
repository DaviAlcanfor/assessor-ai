"""
Erros de domínio do chat.

Ficam aqui, e não nas rotas, porque `services/chat_service.py` tem três consumidores (API HTTP, A2A e
TUI) e cada um apresenta a falha do seu jeito — o serviço não pode conhecer `HTTPException`.
A tradução pra status HTTP mora em `api/exception_handlers.py`.
"""

from assessor_ai.identifiers import ChatID


class ChatError(Exception):
    """Erro base do domínio de chat."""


class ChatNaoEncontrado(ChatError):
    def __init__(self, session_id: ChatID) -> None:
        self.session_id = session_id
        super().__init__("Chat não encontrado.")


class ChatDeOutroUsuario(ChatError):
    def __init__(self, session_id: ChatID) -> None:
        self.session_id = session_id
        super().__init__("Chat pertence a outro usuário.")


class LimiteDeMensagensExcedido(ChatError):
    """Cota de mensagens por janela estourada — ver `core/limiter.py`."""


class FalhaNoAgente(ChatError):
    """
    O grafo não devolveu resposta.

    É um `except Exception` de propósito: abaixo de `runner.executar` estão LLM (timeout, rate
    limit, resposta fora do formato), Postgres (tools + checkpointer), Qdrant e os próprios nós.
    Distinguir cada um exigiria importar os tipos de exceção de quatro SDKs pra tratar todos do
    mesmo jeito — o que muda é só a mensagem de log, e essa vem do `raise ... from` original.
    """


__all__ = [
    "ChatDeOutroUsuario",
    "ChatError",
    "ChatNaoEncontrado",
    "FalhaNoAgente",
    "LimiteDeMensagensExcedido",
]
