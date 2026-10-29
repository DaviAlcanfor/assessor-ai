"""
Transação do turno do chat: todas as escritas de um turno ficam numa só transação do Postgres, que só é
confirmada se o juiz aprovar o turno. Qualquer outro desfecho (recusa, juiz fora do ar, exceção, processo
que cai) desfaz tudo — o padrão é desfazer, nunca confirmar.

Mesmo desenho do `session_context`: um ContextVar aberto pelo runner e lido no ponto de uso
(`PostgresConn.session()`), que chega às tools e ao `to_thread` sem argumento novo em ninguém.
"""

import asyncio
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker


class TransacaoDoTurno:
    def __init__(self) -> None:
        self.aprovada = False  # quem não decide, desfaz
        self.escreveu = False  # só com escrita pendente o juiz fora do ar precisa desfazer o turno
        self._sessao: Session | None = None
        self._lock = threading.Lock()

    @contextmanager
    def usar(self, fabrica: sessionmaker[Session]) -> Iterator[Session]:
        """Uma operação de repository: a sessão do turno dentro de um SAVEPOINT, pra falha de uma tool
        não desfazer as escritas que as outras já fizeram. O lock serializa tool calls paralelas:
        uma `Session` não aguenta uso concorrente."""

        with self._lock:
            if self._sessao is None:
                self._sessao = fabrica()
                event.listen(self._sessao, "after_flush", self._marcar_escrita)

            # ponytail: SAVEPOINT também em leitura — separar leitura de escrita se o custo aparecer.
            with self._sessao.begin_nested():
                yield self._sessao

    def _marcar_escrita(self, *_: object) -> None:
        self.escreveu = True

    def encerrar(self) -> None:
        if self._sessao is None:
            return

        try:
            if self.aprovada:
                self._sessao.commit()
            else:
                self._sessao.rollback()
        finally:
            self._sessao.close()


_atual: ContextVar[TransacaoDoTurno | None] = ContextVar("transacao_do_turno", default=None)


def transacao_atual() -> TransacaoDoTurno | None:
    """A transação do turno em andamento, ou None fora do chat (MCP, scripts, testes de repository)."""

    return _atual.get()


@asynccontextmanager
async def transacao_do_turno() -> AsyncIterator[TransacaoDoTurno]:
    transacao = TransacaoDoTurno()
    token = _atual.set(transacao)
    try:
        yield transacao
    except BaseException:
        transacao.aprovada = False  # exceção no turno nunca confirma, mesmo com o juiz tendo aprovado
        raise
    finally:
        try:
            await asyncio.to_thread(transacao.encerrar)  # commit/rollback são I/O bloqueante
        finally:
            try:
                _atual.reset(token)
            except ValueError:
                # mesmo caso do `session_context`: o finalizer de um async generator abandonado roda
                # num Context diferente do que criou o token.
                pass


__all__ = ["TransacaoDoTurno", "transacao_atual", "transacao_do_turno"]
