"""Alembic environment: synchronous SQLite migrations against the ORM metadata."""

from alembic import context
from sqlalchemy import create_engine, event, pool
from server.admin.models import Base
from server.music import models as music_models  # noqa: F401  registers music tables on Base
from server.storage.database import BUSY_TIMEOUT_MILLISECONDS

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Applies pending revisions on a NullPool connection and disposes the engine.

    Foreign keys are enforced during migrations too, so reversing a revision cannot
    drop a parent table while a child still references it.

    Raises:
        RuntimeError: when the caller requested offline SQL generation.
    """
    if context.is_offline_mode():
        raise RuntimeError("Offline migration generation is not supported; run upgrades online.")
    engine = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)

    @event.listens_for(engine, "connect")
    def apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        """Enables foreign keys and the busy timeout on each migration connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MILLISECONDS}")
        cursor.close()

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
