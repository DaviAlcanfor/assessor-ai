"""Casos de uso das transações financeiras do usuário do turno (tools do agente e MCP).

Aqui moram as regras (resolução de categoria, validação de entrada, parse de datas) e o escopo: o dono dos
dados vem do `session_context()` (`current_user_id()`), nunca de argumento. O SQL fica em
`repositories/financeiro_repository.py` (síncrono: cada chamada vai pra thread com `to_thread`).
"""

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import NotRequired

from app.domain.errors import DadosInvalidos
from app.domain.models.financeiro import PaymentType, TransactionType
from app.infra.context import current_user_id
from app.infra.llm import jev
from app.infra.logging import Logging
from app.infra.redis.cache import buscar_categoria_cache, salvar_categoria_cache
from app.repositories.categoria_repository import CategoriaRecord
from app.repositories.financeiro_repository import (
    CamposTransacao,
    FiltrosTransacao,
    FinanceiroRepository,
    NovaTransacao,
    TransacaoAtualizada,
    TransacaoCriada,
    TransacaoRecord,
    financeiro_repository,
)

logger = Logging.get_logger("financeiro")

_SEM_CATEGORIA = "nenhuma"
_INSTRUCAO_CATEGORIA = (
    "Escolha a categoria financeira que melhor descreve este lançamento. Se nenhuma combinar de verdade, "
    f"escolha '{_SEM_CATEGORIA}' — é melhor sem categoria do que numa errada."
)


def _chave_cache(nome: str, categorias: list[CategoriaRecord]) -> str:
    """Nome sugerido + o conjunto de categorias: se uma categoria for criada ou renomeada, a chave muda e as
    escolhas antigas deixam de valer sozinhas (nada de invalidação manual)."""

    conjunto = "|".join(sorted(c["name"].lower() for c in categorias))
    return hashlib.sha1(f"{nome}\n{conjunto}".encode()).hexdigest()


class TransacaoLancada(TransacaoCriada):
    category: str | None
    aviso: NotRequired[str]


def resolve_transaction_type(type_name: str | None) -> TransactionType:
    """Sem argumento, o tipo padrão (EXPENSES). O schema da tool já restringe o LLM aos três valores
    (`TransactionType`); isso aqui só protege quem chama o service por outro caminho."""

    if not type_name:
        return TransactionType.EXPENSES

    try:
        return TransactionType(type_name.strip().upper())
    except ValueError:
        validos = ", ".join(t.value for t in TransactionType)
        raise DadosInvalidos(f"Tipo de transação inválido: '{type_name}'. Use um de: {validos}.") from None


def _data_hora(texto: str) -> datetime:
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        raise DadosInvalidos(f"Data/hora inválida: '{texto}'. Use ISO 8601 (ex.: 2026-10-21T15:30:00-03:00).") from None


class FinanceiroService:
    def __init__(self, repository: FinanceiroRepository | None = None) -> None:
        self.repository = repository or financeiro_repository

    async def _resolver_categoria(self, category_name: str, contexto: str) -> CategoriaRecord | None:
        """A categoria real que o nome livre do LLM quer dizer, ou None.

        1. Igualdade exata (sem diferenciar maiúsculas): grátis e sem rede.
        2. JeV escolhe entre as categorias que existem de verdade (ou `nenhuma`): nunca inventa uma nova.
           Sem chave do gateway, ou se ele falhar, segue sem categoria — o chamador avisa o usuário.
        """

        categorias = await asyncio.to_thread(self.repository.categorias)
        nome = category_name.strip().lower()

        if exata := next((c for c in categorias if c["name"].lower() == nome), None):
            return exata

        if not categorias or not jev.disponivel():
            return None

        chave = _chave_cache(nome, categorias)
        escolha = await self._cache_buscar(chave)

        if escolha is None:
            opcoes = {c["name"]: c["description"] or c["name"] for c in categorias}
            opcoes[_SEM_CATEGORIA] = "nenhuma das categorias acima combina"

            try:
                escolha = await jev.escolher(
                    "categoria_transacao",
                    f"Categoria sugerida: {category_name}\nLançamento: {contexto}",
                    _INSTRUCAO_CATEGORIA,
                    opcoes,
                )
            except Exception as e:
                logger.warning("JeV não resolveu a categoria '%s': %s", category_name, e)
                return None  # falha não vai pro cache: a próxima tentativa pergunta de novo

            await self._cache_salvar(chave, escolha)

        return next((c for c in categorias if c["name"] == escolha), None)

    async def _cache_buscar(self, chave: str) -> str | None:
        """Redis fora do ar é só um cache miss: o lançamento não depende dele."""

        try:
            return await asyncio.to_thread(buscar_categoria_cache, chave)
        except Exception as e:
            logger.warning("Cache de categoria indisponível (leitura): %s", e)
            return None

    async def _cache_salvar(self, chave: str, escolha: str) -> None:
        try:
            await asyncio.to_thread(salvar_categoria_cache, chave, escolha)
        except Exception as e:
            logger.warning("Cache de categoria indisponível (escrita): %s", e)

    async def adicionar(
        self,
        amount: float,
        source_text: str,
        occurred_at: str | None = None,
        type_name: str | None = None,
        category_id: int | None = None,
        category_name: str | None = None,
        description: str | None = None,
        payment_method: PaymentType | None = None,
    ) -> TransacaoLancada:
        categoria = None
        if category_id is None and category_name:
            categoria = await self._resolver_categoria(category_name, description or source_text)
            category_id = categoria["id"] if categoria else None

        dados = NovaTransacao(
            amount=amount,
            type=resolve_transaction_type(type_name),
            category_id=category_id,
            category_name=None,  # já resolvida aqui; o repository só grava o id
            description=description,
            payment_method=payment_method,
            occurred_at=_data_hora(occurred_at) if occurred_at else datetime.now(UTC),
            source_text=source_text,
        )

        criada = await asyncio.to_thread(self.repository.adicionar, current_user_id(), dados)
        lancada = TransacaoLancada(**criada, category=categoria["name"] if categoria else None)

        if category_name and category_id is None:
            lancada["aviso"] = (
                f"Não achei uma categoria para '{category_name}': a transação ficou sem categoria. "
                "Avise o usuário e, se quiser, pergunte qual categoria usar."
            )

        return lancada

    async def saldo_total(self) -> float:
        return await asyncio.to_thread(self.repository.saldo_total, current_user_id())

    async def saldo_do_dia(self, date_local: str) -> float:
        return await asyncio.to_thread(self.repository.saldo_do_dia, current_user_id(), date_local)

    async def consultar(
        self,
        date_from_local: str | None = None,
        date_to_local: str | None = None,
        type_name: str | None = None,
        source_text: str | None = None,
    ) -> list[TransacaoRecord]:
        filtros = FiltrosTransacao(
            date_from_local=date_from_local,
            date_to_local=date_to_local,
            source_text=source_text,
        )
        if type_name:
            filtros["type"] = resolve_transaction_type(type_name)

        return await asyncio.to_thread(self.repository.consultar, current_user_id(), filtros)

    async def atualizar(
        self,
        id: int | None = None,
        match_text: str | None = None,
        date_local: str | None = None,
        amount: float | None = None,
        type_name: str | None = None,
        category_id: int | None = None,
        category_name: str | None = None,
        description: str | None = None,
        payment_method: PaymentType | None = None,
        occurred_at: str | None = None,
    ) -> TransacaoAtualizada | None:
        """`None` = o id informado não existe (ou é de outro usuário)."""

        if category_id is None and category_name:
            categoria = await self._resolver_categoria(category_name, description or match_text or "")
            if categoria is None:
                raise DadosInvalidos(
                    f"Não achei uma categoria para '{category_name}': nada foi alterado. "
                    "Pergunte ao usuário qual categoria usar."
                )
            category_id = categoria["id"]

        campos = CamposTransacao()
        if amount is not None:         campos["amount"] = amount
        if type_name is not None:      campos["type"] = resolve_transaction_type(type_name)
        if category_id is not None:    campos["category_id"] = category_id
        if description is not None:    campos["description"] = description
        if payment_method is not None: campos["payment_method"] = payment_method
        if occurred_at is not None:    campos["occurred_at"] = _data_hora(occurred_at)

        if not campos:
            raise DadosInvalidos("Nada para atualizar: forneça pelo menos um campo.")

        if id is None and not (match_text and date_local):
            raise DadosInvalidos("Sem 'id': informe match_text E date_local para localizar o registro.")

        return await asyncio.to_thread(
            self.repository.atualizar, current_user_id(), id, match_text, date_local, campos
        )


financeiro_service = FinanceiroService()


__all__ = ["FinanceiroService", "TransacaoLancada", "financeiro_service", "resolve_transaction_type"]
