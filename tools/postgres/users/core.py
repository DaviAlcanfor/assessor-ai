from config.logging import get_logger

from tools.postgres.connection import get_conn

logger = get_logger("pg_users")


def garantir_usuario(user_id: str) -> None:
    """
    Garante que o usuário exista na tabela `users` do Postgres.

    Idempotente (ON CONFLICT DO NOTHING) — chamada junto com
    tools.mongo.users.core.garantir_usuario, usando o mesmo user_id, para
    manter os dois bancos com o mesmo identificador.
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING;",
                (user_id,)
            )
            conn.commit()


__all__ = ["garantir_usuario"]
