from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from assessor_ai.core.config import settings

# Todo model precisa ser importado aqui: com os models fatiados por feature, o que não for
# importado some do `Base.metadata` e o --autogenerate gera um DROP da tabela correspondente.
from assessor_ai.graph.tools.agenda.models import Event  # noqa: F401
from assessor_ai.graph.tools.financeiro.models import (  # noqa: F401
    Category,
    Transaction,
)
from assessor_ai.graph.tools.usuarios.models import User  # noqa: F401
from assessor_ai.infra.postgres import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# URL do banco vem de core/config.py (fonte única de env vars do projeto),
# nunca de alembic.ini nem de parsing próprio do .env.
config.set_main_option("sqlalchemy.url", settings.POSTGRES_URL.get_secret_value())

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# As tabelas `checkpoint*` são criadas e migradas pelo próprio LangGraph
# (`AsyncPostgresSaver.setup()`), não pelo Alembic — sem esse filtro elas ficam de fora do
# `target_metadata` e o --autogenerate gera um DROP delas, que apaga o histórico de conversa
# de todos os usuários. Verificado com `alembic check`.
_TABELAS_EXTERNAS = ("checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations")


def include_object(object, name, type_, reflected, compare_to) -> bool:
    if type_ == "table" and name in _TABELAS_EXTERNAS:
        return False

    return not (
        type_ == "index" and getattr(object.table, "name", None) in _TABELAS_EXTERNAS
    )



# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
