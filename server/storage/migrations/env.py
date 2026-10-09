"""Alembic environment: synchronous SQLite migrations against the ORM metadata."""

from alembic import context
from sqlalchemy import create_engine, pool
from server.admin.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Applies pending revisions on a NullPool connection and disposes the engine.

    Raises:
        RuntimeError: when the caller requested offline SQL generation.
    """
    if context.is_offline_mode():
        raise RuntimeError("Offline migration generation is not supported; run upgrades online.")
    engine = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
