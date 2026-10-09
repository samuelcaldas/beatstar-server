"""Applies Alembic revisions to a SQLite file; used by application startup and tests."""

from pathlib import Path
from alembic import command
from alembic.config import Config

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent


def upgrade_to_head(database_path: str) -> None:
    """Upgrades the SQLite file at database_path to the newest revision.

    Args:
        database_path: Filesystem path of the SQLite database; created if missing.

    Raises:
        alembic.util.exc.CommandError: when a revision cannot be applied.
    """
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIRECTORY))
    escaped_url = f"sqlite:///{database_path}".replace("%", "%%")
    config.set_main_option("sqlalchemy.url", escaped_url)
    command.upgrade(config, "head")
