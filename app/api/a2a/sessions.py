import asyncio

from app.domain.types import ChatID, UserID
from app.services import chat_service


class SessoesA2A:
    """`context_id` do protocolo A2A → (usuário, chat) do Assessor.AI.

    O `context_id` é a chave da conversa pro cliente A2A; aqui ele precisa virar um usuário e um chat
    reais, que são criados na primeira mensagem do contexto e reaproveitados nas seguintes.

    ponytail: mapa em memória (perdido no restart, não compartilhado entre workers) — troca por
    Redis (`infra/redis`) se o A2A rodar com múltiplos processos/instâncias.
    ponytail: um lock global em vez de um por `context_id` — serializa toda criação de sessão A2A,
    não só a do mesmo `context_id`, mas o tráfego do A2A é baixo o bastante pra isso não importar.
    Trocar por lock por-context_id se o volume crescer.
    """

    def __init__(self) -> None:
        self._sessoes: dict[str, tuple[UserID, ChatID]] = {}
        self._lock = asyncio.Lock()

    async def obter(self, context_id: str) -> tuple[UserID, ChatID]:
        if context_id in self._sessoes:
            return self._sessoes[context_id]

        async with self._lock:
            # re-checa depois de pegar o lock: outra task pode ter criado enquanto esperávamos
            if context_id not in self._sessoes:
                self._sessoes[context_id] = await chat_service.iniciar_sessao()

        return self._sessoes[context_id]

    def limpar(self) -> None:
        self._sessoes.clear()


sessoes = SessoesA2A()

__all__ = ["SessoesA2A", "sessoes"]
