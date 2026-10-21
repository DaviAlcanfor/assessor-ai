"""Persistência das categorias financeiras (tabela global, não é por usuário)."""

from typing import TypedDict

from sqlalchemy import select

from app.infra.postgres import postgres
from app.infra.postgres.models import Category


class CategoriaRecord(TypedDict):
    id: int
    name: str
    description: str | None


def listar() -> list[CategoriaRecord]:
    """Todas as categorias, ordenadas por nome. Síncrono: quem chama de código async usa `to_thread`."""

    with postgres.session() as s:
        categorias = s.scalars(select(Category).order_by(Category.name)).all()

        return [CategoriaRecord(id=c.id, name=c.name, description=c.description) for c in categorias]


__all__ = ["CategoriaRecord", "listar"]
