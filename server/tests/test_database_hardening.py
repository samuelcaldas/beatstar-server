"""SQLite connection hardening and legacy schema preservation on disposable databases."""

from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository
from server.models.player import PlayerProfile

LEGACY_TABLES = ("players", "song_scores", "player_friends", "player_brags")


async def test_connections_enforce_foreign_keys_and_busy_timeout(tmp_path):
    """Breaks if a connection is opened without foreign_keys or the busy timeout pragmas."""
    database = DatabaseManager(str(tmp_path / "pragmas.db"))
    await database.initialize()

    async with database.connect() as connection:
        foreign_keys = await (await connection.execute("PRAGMA foreign_keys")).fetchone()
        busy_timeout = await (await connection.execute("PRAGMA busy_timeout")).fetchone()

    assert foreign_keys[0] == 1
    assert busy_timeout[0] == 5000


async def test_reinitialization_preserves_legacy_rows_and_columns(tmp_path):
    """Breaks if initialize() rewrites legacy tables or drops rows on a populated database."""
    database = DatabaseManager(str(tmp_path / "legacy.db"))
    await database.initialize()
    await PlayerRepository(database).save(
        PlayerProfile(cinta="legacy-cinta", clide="legacy", coins=7, gems=3)
    )
    columns_before = await _table_columns(database)

    await database.initialize()

    stored = await PlayerRepository(database).get_by_cinta("legacy-cinta")
    assert stored.coins == 7
    assert stored.gems == 3
    assert await _table_columns(database) == columns_before


async def _table_columns(database: DatabaseManager) -> dict[str, list[tuple]]:
    """Returns PRAGMA table_info for every legacy table, keyed by table name."""
    columns = {}
    async with database.connect() as connection:
        for table in LEGACY_TABLES:
            rows = await (await connection.execute(f"PRAGMA table_info({table})")).fetchall()
            columns[table] = [tuple(row) for row in rows]
    return columns
