"""Music-domain schema: creation order, foreign key preservation and reversible migrations."""

import asyncio
import sqlite3

import pytest

from server.storage.database import DatabaseManager
from server.storage.migrations.runner import downgrade_to, upgrade_to_head
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository

MUSIC_TABLES = ("songs", "assets", "chart_revisions", "build_jobs", "releases", "audit_events")
ADMIN_USER_ID = "00000000-0000-4000-8000-000000000001"


def _connect(database_file) -> sqlite3.Connection:
    """Opens a connection with foreign key enforcement, as the application does."""
    connection = sqlite3.connect(database_file)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _creation_order(connection: sqlite3.Connection) -> dict[str, int]:
    """Returns each table's position in sqlite_master, which records creation order."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid"
    ).fetchall()
    return {name: position for position, (name,) in enumerate(rows)}


def _insert_chain(connection: sqlite3.Connection) -> None:
    """Inserts one valid row per music table, respecting the dependency order."""
    connection.execute(
        'INSERT INTO "user" (id, email, hashed_password, is_active, is_superuser, is_verified) '
        "VALUES (?, 'admin@example.com', 'x', 1, 1, 1)",
        (ADMIN_USER_ID,),
    )
    connection.execute(
        "INSERT INTO songs (id, title, artist, status, revision, created_at, updated_at) "
        "VALUES ('song-1', 'Title', 'Artist', 'draft', 1, 1, 1)"
    )
    connection.execute(
        "INSERT INTO assets (id, song_id, kind, storage_key, sha256, byte_size, content_type, created_at) "
        "VALUES ('asset-1', 'song-1', 'audio', 'key-1', 'a', 1, 'audio/ogg', 1)"
    )
    connection.execute(
        "INSERT INTO chart_revisions (id, song_id, revision_number, schema_version, document, sha256, created_at) "
        "VALUES ('chart-1', 'song-1', 1, 1, '{}', 'b', 1)"
    )
    connection.execute(
        "INSERT INTO build_jobs (id, song_id, chart_revision_id, status, attempts, idempotency_key, created_at, updated_at) "
        "VALUES ('job-1', 'song-1', 'chart-1', 'succeeded', 1, 'idem-1', 1, 1)"
    )
    connection.execute(
        "INSERT INTO releases (id, song_id, chart_revision_id, build_job_id, version, client_target, status, created_at) "
        "VALUES ('release-1', 'song-1', 'chart-1', 'job-1', 1, '36.1.4.9545', 'published', 1)"
    )


def test_music_tables_are_created_after_the_tables_they_reference(tmp_path):
    """Breaks if a revision creates a referencing table before its parent exists."""
    database_file = tmp_path / "order.db"
    upgrade_to_head(str(database_file))

    with _connect(database_file) as connection:
        order = _creation_order(connection)
        for table in MUSIC_TABLES:
            assert table in order, f"{table} was not created"
            for foreign_key in connection.execute(f"PRAGMA foreign_key_list({table})").fetchall():
                target = foreign_key[2]
                assert target in order, f"{table} references missing table {target}"
                assert order[target] < order[table], f"{table} created before {target}"


def test_foreign_keys_reject_orphan_assets(tmp_path):
    """Breaks if an asset can exist without its song."""
    database_file = tmp_path / "orphan.db"
    upgrade_to_head(str(database_file))

    with _connect(database_file) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO assets (id, song_id, kind, storage_key, sha256, byte_size, content_type, created_at) "
                "VALUES ('asset-x', 'no-such-song', 'audio', 'key-x', 'a', 1, 'audio/ogg', 1)"
            )


def test_release_chain_blocks_deleting_its_build_job_and_chart_revision(tmp_path):
    """Breaks if a published release loses the build job or chart revision it was built from."""
    database_file = tmp_path / "restrict.db"
    upgrade_to_head(str(database_file))

    with _connect(database_file) as connection:
        _insert_chain(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM build_jobs WHERE id = 'job-1'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM chart_revisions WHERE id = 'chart-1'")


def test_songs_with_children_cannot_be_hard_deleted(tmp_path):
    """Breaks if deleting a song silently removes its assets, charts, jobs or releases."""
    database_file = tmp_path / "song-restrict.db"
    upgrade_to_head(str(database_file))

    with _connect(database_file) as connection:
        _insert_chain(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM songs WHERE id = 'song-1'")


def test_audit_actor_is_cleared_when_administrator_is_removed(tmp_path):
    """Breaks if removing an administrator erases or rejects the audit history."""
    database_file = tmp_path / "audit.db"
    upgrade_to_head(str(database_file))

    with _connect(database_file) as connection:
        _insert_chain(connection)
        connection.execute(
            "INSERT INTO audit_events (id, actor_id, action, target_type, target_id, created_at) "
            "VALUES ('event-1', ?, 'song.create', 'song', 'song-1', 1)",
            (ADMIN_USER_ID,),
        )
        connection.execute('DELETE FROM "user" WHERE id = ?', (ADMIN_USER_ID,))
        actor = connection.execute("SELECT actor_id FROM audit_events WHERE id = 'event-1'").fetchone()

    assert actor == (None,)


def test_downgrade_and_upgrade_keep_legacy_rows_and_foreign_key_order(tmp_path):
    """Breaks if reversing the music revision drops legacy data or violates dependency order."""
    database_file = tmp_path / "round-trip.db"
    database = DatabaseManager(str(database_file))
    asyncio.run(database.initialize())
    asyncio.run(
        PlayerRepository(database).save(
            PlayerProfile(cinta="round-trip-cinta", clide="round", coins=4, gems=1)
        )
    )
    upgrade_to_head(str(database_file))

    downgrade_to(str(database_file), "0001_admin_auth")
    with _connect(database_file) as connection:
        assert "songs" not in _creation_order(connection)
    upgrade_to_head(str(database_file))

    stored = asyncio.run(PlayerRepository(database).get_by_cinta("round-trip-cinta"))
    assert stored.coins == 4
    with _connect(database_file) as connection:
        assert set(MUSIC_TABLES) <= set(_creation_order(connection))
