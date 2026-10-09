"""Alembic migrations on disposable SQLite databases: new admin tables, legacy preservation."""

import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from server.admin.models import Base
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager
from server.storage.migrations.runner import upgrade_to_head
from server.storage.player_repository import PlayerRepository


def _table_names(database_file) -> set[str]:
    """Returns table names currently present in the SQLite file."""
    with sqlite3.connect(database_file) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


async def test_upgrade_creates_admin_tables_and_keeps_legacy_rows(tmp_path):
    """Breaks if the first revision drops legacy data or never creates the admin user table."""
    database_file = tmp_path / "upgrade.db"
    database = DatabaseManager(str(database_file))
    await database.initialize()
    await PlayerRepository(database).save(
        PlayerProfile(cinta="migrated-cinta", clide="migrated", coins=11, gems=2)
    )

    upgrade_to_head(str(database_file))

    assert {"user", "accesstoken"} <= _table_names(database_file)
    stored = await PlayerRepository(database).get_by_cinta("migrated-cinta")
    assert stored.coins == 11


def test_upgrade_is_idempotent(tmp_path):
    """Breaks if a second startup fails or rewrites an already-migrated schema."""
    database_file = tmp_path / "twice.db"
    upgrade_to_head(str(database_file))
    upgrade_to_head(str(database_file))

    assert {"user", "accesstoken"} <= _table_names(database_file)


def test_migrated_schema_matches_orm_metadata(tmp_path):
    """Breaks if a revision and the ORM models drift apart."""
    database_file = tmp_path / "drift.db"
    upgrade_to_head(str(database_file))

    engine = create_engine(f"sqlite:///{database_file}")
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert differences == []
