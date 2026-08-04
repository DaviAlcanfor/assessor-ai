from sqlalchemy.dialects.postgresql import insert

from assessor_ai.tools.postgres.connection import get_session
from assessor_ai.tools.postgres.models import User
from config.logging import get_logger

logger = get_logger("pg_users")


def garantir_usuario(user_id: str) -> None:
    """
    Garante que o usuário exista na tabela `users` do Postgres.

    Idempotente (ON CONFLICT DO NOTHING) — chamada junto com
    tools.mongo.users.core.garantir_usuario, usando o mesmo user_id, para
    manter os dois bancos com o mesmo identificador.
    """

    with get_session() as session:
        stmt = insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])
        session.execute(stmt)


__all__ = ["garantir_usuario"]
