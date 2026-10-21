"""
Todas as exceptions de domínio do projeto, num lugar só.

Cada classe carrega a tradução HTTP (`status_code`, `code`) e a mensagem que pode ir pro cliente
(`public_message`). `str(exc)` é a mensagem interna: vai pro log, nunca pra resposta.

Ficam no domínio, e não nas rotas, porque os services têm vários consumidores (API HTTP, A2A, MCP e
TUI) e cada um apresenta a falha do seu jeito — o serviço não pode conhecer `HTTPException`. O status
é um `int` (`HTTPStatus`), de propósito: o domínio não importa FastAPI.
"""

from enum import StrEnum
from http import HTTPStatus

from app.domain.types import ChatID


class ErrorCode(StrEnum):
    CHAT_NAO_ENCONTRADO = "chat_nao_encontrado"
    CHAT_DE_OUTRO_USUARIO = "chat_de_outro_usuario"
    LIMITE_DE_MENSAGENS = "limite_de_mensagens"
    FALHA_NO_AGENTE = "falha_no_agente"
    ERRO_INTERNO = "erro_interno"
    ERRO_NO_CHAT = "erro_no_chat"
    DADOS_INVALIDOS = "dados_invalidos"
    REGISTRO_NAO_ENCONTRADO = "registro_nao_encontrado"
    SERVICO_EXTERNO_INDISPONIVEL = "servico_externo_indisponivel"


class AssessorError(Exception):
    """Raiz de tudo que o projeto levanta de propósito."""


class DomainError(AssessorError):
    """Erro de domínio traduzível pra HTTP; a subclasse só sobrescreve o que muda."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: ErrorCode = ErrorCode.ERRO_INTERNO
    public_message: str = "Não foi possível concluir a operação."


class DadosInvalidos(DomainError):
    """Entrada que o service não consegue usar (campo faltando, formato errado). A mensagem é escrita
    pra quem chamou — o LLM numa tool, o cliente numa rota — entender o que corrigir."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = ErrorCode.DADOS_INVALIDOS

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.public_message = mensagem


class RegistroNaoEncontrado(DomainError):
    """Nenhum registro do usuário bate com o pedido."""

    status_code = HTTPStatus.NOT_FOUND
    code = ErrorCode.REGISTRO_NAO_ENCONTRADO

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.public_message = mensagem


class ServicoExternoIndisponivel(DomainError):
    """Uma API de terceiros (cotação, Banco Central...) não respondeu direito. A mensagem não carrega URL
    nem detalhe da falha: pode ir direto pro usuário."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = ErrorCode.SERVICO_EXTERNO_INDISPONIVEL

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.public_message = mensagem


class UsuarioDaSessaoNaoDefinido(DomainError):
    """Tool, repository ou rota chamados fora de `session_context()`: sem usuário, sem dado."""

    def __init__(self) -> None:
        super().__init__("current_user_id não definido — chame dentro de session_context().")


class ChatError(DomainError):
    """Erro base dos casos de uso de chat (`services/chat_service.py`)."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = ErrorCode.ERRO_NO_CHAT


class ChatNaoEncontrado(ChatError):
    status_code = HTTPStatus.NOT_FOUND
    code = ErrorCode.CHAT_NAO_ENCONTRADO
    public_message = "Chat não encontrado."

    def __init__(self, session_id: ChatID) -> None:
        self.session_id = session_id
        super().__init__(f"Chat {session_id} não encontrado.")


class ChatDeOutroUsuario(ChatError):
    status_code = HTTPStatus.FORBIDDEN
    code = ErrorCode.CHAT_DE_OUTRO_USUARIO
    public_message = "Chat pertence a outro usuário."

    def __init__(self, session_id: ChatID) -> None:
        self.session_id = session_id
        super().__init__(f"Chat {session_id} pertence a outro usuário.")


class LimiteDeMensagensExcedido(ChatError):
    """Cota de mensagens por janela estourada — ver `infra/redis`."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    code = ErrorCode.LIMITE_DE_MENSAGENS
    public_message = "Você atingiu o limite de mensagens. Tente novamente em alguns instantes."


class FalhaNoAgente(ChatError):
    """
    O grafo não devolveu resposta.

    É um `except Exception` de propósito: abaixo de `runner.executar` estão LLM (timeout, rate
    limit, resposta fora do formato), Postgres (tools + checkpointer), Qdrant e os próprios nós.
    Distinguir cada um exigiria importar os tipos de exceção de quatro SDKs pra tratar todos do
    mesmo jeito — o que muda é só a mensagem de log, e essa vem do `raise ... from` original.
    """

    status_code = HTTPStatus.BAD_GATEWAY
    code = ErrorCode.FALHA_NO_AGENTE
    public_message = "Não foi possível processar a mensagem."


__all__ = [
    "AssessorError",
    "ChatDeOutroUsuario",
    "ChatError",
    "ChatNaoEncontrado",
    "DadosInvalidos",
    "DomainError",
    "ErrorCode",
    "FalhaNoAgente",
    "LimiteDeMensagensExcedido",
    "RegistroNaoEncontrado",
    "ServicoExternoIndisponivel",
    "UsuarioDaSessaoNaoDefinido",
]
