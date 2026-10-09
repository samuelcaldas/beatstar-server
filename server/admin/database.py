"""Async SQLAlchemy engine for administration tables with the same SQLite pragmas as legacy access."""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from server.storage.database import BUSY_TIMEOUT_MILLISECONDS


def create_admin_engine(database_path: str) -> AsyncEngine:
    """Creates an engine whose every pooled connection enforces foreign keys.

    Args:
        database_path: Filesystem path of the SQLite database shared with legacy tables.

    Returns:
        An AsyncEngine using the aiosqlite driver.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        """Sets per-connection pragmas; SQLite resets them for each new connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MILLISECONDS}")
        cursor.close()

    return engine


def create_admin_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Returns a session factory that keeps loaded attributes usable after commit."""
    return async_sessionmaker(engine, expire_on_commit=False)
