"""
Escopo do usuário do turno: um `ContextVar` só, lido por quem precisa filtrar por dono (repositories de
Postgres, Mongo e Qdrant). Quem sabe quem é o usuário abre o escopo com `session_context()`: o runner do
grafo (cobre API, TUI e A2A) e o middleware do MCP.

Tool e repository nunca recebem `user_id` como argumento — o LLM poderia escolher o de outra pessoa.
Fora de um `session_context()`, `current_user_id()` levanta: não existe usuário "padrão" que leia dado real.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from app.domain.errors import UsuarioDaSessaoNaoDefinido
from app.domain.types import UserID, UserIDField

_user_id: ContextVar[UUID | None] = ContextVar("current_user_id", default=None)


@contextmanager
def session_context(user_id: UUID | str) -> Generator[None]:
    token = _user_id.set(UUID(str(user_id)))
    try:
        yield
    finally:
        # ponytail: engole ValueError — quando o consumidor do SSE cai no meio do stream, o async
        # generator de `runner.executar_stream` vira órfão e o event loop o fecha via GeneratorExit
        # num Context novo (asyncgen finalizer), diferente daquele onde o token foi criado. `.reset()`
        # nesse Context sempre falha; não há "certo" a fazer além de ignorar — o ContextVar órfão
        # some junto com o Context quando ele for coletado.
        try:
            _user_id.reset(token)
        except ValueError:
            pass


def current_user_id() -> UUID:
    """Usuário do turno como UUID (Postgres). Levanta fora de `session_context()`."""

    user_id = _user_id.get()
    if user_id is None:
        raise UsuarioDaSessaoNaoDefinido()
    return user_id


def current_user() -> UserID:
    """O mesmo usuário como `UserID` (string) — a forma que Mongo e Qdrant usam."""

    return UserIDField(str(current_user_id()))


__all__ = ["current_user", "current_user_id", "session_context"]
